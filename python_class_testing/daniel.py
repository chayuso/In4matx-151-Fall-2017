#Test Class
from database import Database

class Test():
    def __init__(self,database):
        self.string = ""
        self.database = database

    def print_age(self,username):
        print(self.database.data_list["users"][username]["age"])
        
    def test_add(self, username):
        self.database.add_user(username)
        
        print(self.database.data_list)
        ##   print(self.database.data_list[i])

if __name__ == '__main__':
    database_object = Database("accounts")
    database_object.load_json_database()
    
    bot = Test(database_object)
    #bot.print_age("chayuso#5309")
    
    bot.test_add("Daniel")
    
