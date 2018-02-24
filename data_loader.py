from sklearn.datasets.svmlight_format import load_svmlight_file

Q1_TRAIN_PATH = "data/train.txt"
Q1_TEST_PATH = "data/test.txt"


def load_Q1_data():
    X_train, y_train = load_svmlight_file(Q1_TRAIN_PATH)