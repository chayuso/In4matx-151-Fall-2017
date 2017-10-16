from database import Database


class Prototype:
    def __init__(self):
        Database("accounts.txt").load_json_database()

        




if __name__ == "__main__":
    Prototype()
