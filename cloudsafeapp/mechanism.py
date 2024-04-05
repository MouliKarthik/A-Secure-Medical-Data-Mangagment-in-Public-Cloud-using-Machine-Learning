import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder
from Cryptodome.Cipher import AES
from base64 import b64encode, b64decode
import hashlib
from Cryptodome.Random import get_random_bytes
import os
from django.conf import settings
from uuid import uuid4

# for timer
import time


def get_it_encrypted(df, password):
    # ---- MACHINE LEARNING ----
    print("[STATUS] Upload File Started")
    # Getting Number of rows and cols
    row, col = df.shape

    # Find data type and null values
    col_names = list(df.columns)
    data_type = df.dtypes
    print("[STATUS] Found Data Type")
    null_per = df.isna().sum() / row * 100
    print("[STATUS] Calculated Percentage of NULL values")

    # Find unique values and categorical data
    unique_per = []
    categorical = []
    for c in col_names:
        b = df.pivot_table(index=[c], aggfunc="size")
        unique = 0
        for i in b.array:
            if i == 1:
                unique += 1
        col_unique_per = unique / row * 100
        if col_unique_per <= 2:
            categorical.append(1)
        else:
            categorical.append(0)
        unique_per.append(col_unique_per)
    print("[STATUS] Calculated Percentage of Unique values")
    print("[STATUS] Found Categorical data")

    # transform object data to string and use that find correlation
    le = LabelEncoder()
    le.fit([1, 2, 2, 6])
    encdf = df.copy(deep=True)
    for i in col_names:
        if encdf[i].dtype == "object":
            encdf[i] = le.fit_transform(df[i].astype("str"))
    corrMatrix = encdf.corr()
    corr = [0 for i in range(col)]
    for i in range(col):
        for j in range(i - 1):
            if (
                corrMatrix[col_names[i]][col_names[j]] > 0.75
                or corrMatrix[col_names[i]][col_names[j]] < -0.75
            ):
                corr[i] = 1
    print("[STATUS] Calculated Correlation Matrix")

    # Find pattern based sensitive data
    sensitive = []
    patterns = ["id", "aadhaar", "ssn", "name", "phone", "address", "mail", "location"]
    for c in col_names:
        f = 0
        c = c.lower()
        for pattern in patterns:
            if pattern in c:
                sensitive.append(1)
                f = 1
                break
        if f == 0:
            sensitive.append(0)
    print("[STATUS] Found Pattern based Sensitive data")

    # Create X_pred
    X_pred = np.zeros([col, 6], dtype=int)
    for i in range(col):
        for j in range(6):
            if j == 0:
                if data_type.iloc[i] == "int":
                    X_pred[i][0] = 1
                elif data_type.iloc[i] == "float":
                    X_pred[i][0] = 2
                elif data_type.iloc[i] == "object":
                    X_pred[i][0] = 3
                else:
                    X_pred[i][0] = 4
            elif j == 1:
                X_pred[i][1] = int(null_per.iloc[i] * 100)
            elif j == 2:
                X_pred[i][2] = unique_per[i]
            elif j == 3:
                X_pred[i][3] = categorical[i]
            elif j == 4:
                X_pred[i][4] = corr[i]
            elif j == 5:
                X_pred[i][5] = sensitive[i]
    print("[STATUS] Data Analyzed Successfully")

    # Make predictions using model
    # filename = "path to model .sav"
    # filename = "D:\\Projects\\ThirdYearMiniProject\\django\\trial1\\cloudsafe\\static\\6_feature_model_updated.sav"
    filename = os.path.join(settings.STATIC_ROOT, "6_feature_model_updated.sav")
    loaded_model = pickle.load(open(filename, "rb"))
    r_pred = loaded_model.predict(X_pred)
    print("[STATUS] Sensitivity Prediction Successfull")

    start_time = time.time()
    newdf = pd.DataFrame()
    for i in range(row):
        data = {}
        salt = get_random_bytes(AES.block_size)
        private_key = hashlib.scrypt(
            password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        for j in range(len(col_names)):
            if r_pred[j] == 1:
                if col_names[j] == "id":
                    encrypted = encrypt_message(df.at[i, col_names[j]], private_key)
                    data["did"] = encrypted
                else:
                    encrypted = encrypt_message(df.at[i, col_names[j]], private_key)
                    data[col_names[j]] = encrypted
            else:
                data[col_names[j]] = str(df.at[i, col_names[j]])
        data["salt"] = b64encode(salt).decode("utf-8")
        data["id"] = uuid4().hex
        newdf = newdf._append(data, ignore_index=True)  # Append encrypted data to newdf
    sensitivity_str = ",".join(map(str, r_pred))
    print("[STATUS] Data Encrypted Successfully")
    print("--- %s seconds ---" % (time.time() - start_time))
    return newdf, sensitivity_str


def get_it_decrypted(data, password):
    start_time = time.time()
    decrypted_data = []
    for row in data:
        decrypted_row = {}
        salt = b64decode(row["salt"])
        private_key = hashlib.scrypt(
            password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        for key, value in row.items():
            if key == "salt":
                break
            if type(value) is dict:
                decrypted_row[key] = decrypt_message(value, private_key)
            else:
                decrypted_row[key] = value
        decrypted_data.append(decrypted_row)
    print("--- %s seconds ---" % (time.time() - start_time))
    return decrypted_data


def encrypt_message(plain_text, key):
    plain_text = str(plain_text)
    cipher_config = AES.new(key, AES.MODE_GCM)
    # return a dictionary with the encrypted text
    cipher_text, tag = cipher_config.encrypt_and_digest(bytes(plain_text, "utf-8"))
    return {
        "cipher_text": b64encode(cipher_text).decode("utf-8"),
        "nonce": b64encode(cipher_config.nonce).decode("utf-8"),
        "tag": b64encode(tag).decode("utf-8"),
    }


def decrypt_message(enc_dict, private_key):
    # decode the dictionary entries from base64
    cipher_text = b64decode(enc_dict["cipher_text"])
    nonce = b64decode(enc_dict["nonce"])
    tag = b64decode(enc_dict["tag"])
    cipher = AES.new(private_key, AES.MODE_GCM, nonce=nonce)
    decrypted = cipher.decrypt_and_verify(cipher_text, tag)
    return str(decrypted)[2:-1]


# def test_it():
#     # df = pd.read_csv("path to a fake data csv")
#     df = pd.read_csv(
#         "D:\\Projects\\ThirdYearMiniProject\\pandas\\trial1\\fakedatamaker\\out\\fake_data_10.csv"
#     )
#     print("[STATUS] File read successfully !")
#     newdf = get_it_encrypted(df, "password")
#     print(newdf)
#     print("TEST PASSED SUCCESSFULLY !")


# test_it()
