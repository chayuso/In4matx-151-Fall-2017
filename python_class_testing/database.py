import json
import datetime

########################################
#JSON to Dictionary example
jsonData = '{"name": "anivia","stats": {"health": 51.4,"health_regen": 0.651,"attack_dmg": 5.3,"armor": 2.09,"magic_resist": 3,"move_speed": 33,"mana": 33.4,"magic_dmg": 0,"mana_regen": 0.6,"critical": 0},"moves": {"passive": "Rebirth","q": "Flash Frost","w": "Crystallize","e": "Frostbite","r": "Glacial Storm"}}'
jsonToPython = json.loads(jsonData)
#print(jsonToPython["stats"]["health"])

#Dictionary to JSON string example
pythonDictionary = {'name':'Bob', 'age':44, 'isEmployed':True}
dictionaryToJson = json.dumps(pythonDictionary)
#print(dictionaryToJson)
########################################

class Database():
    def __init__(self,database_file_name:str):
        """
        Requires the name of the database file located under /database
        directory.
        """
        self.data_list = {}
        self.database_name = database_file_name

    def write_bkup_database(self):
        """
        Backs up the database in case of loss in a seperate _bk.txt file.
        """
        backup_file = open("database/"+self.database_name+"_bk.txt",'w',encoding="utf8")
        backup_file.write(json.dumps(self.data_list))
        backup_file.close()
        
    def load_json_database(self):
        """
        This will be initially called when the bot is first ran.
        Loads the database text file into variable self.data_list dictionary.
        """
        try:
            infile = open("database/"+self.database_name+".txt",'r',encoding="utf8")
        except:
            print("Error: Cannot locate database"+self.database_name+".txt file in directory!")          
        temp_backup_file_str = ""
        self.data_list = {}
        for line in infile:
            self.data_list =json.loads(line.strip("\n"))
            temp_backup_file_str+=line
        infile.close()
        print('Database: "'+ self.database_name+'" successfully loaded!')

        #Save a bkup file after loading in the case the
        #database is lost wheb attempting to open or reading.
        self.write_bkup_database()
        print('Init database bkup written...\n')
            
    def write_json_database(self):
        """
        Copies self.data_list dictionary to convert to json, then writes
        in the database text file.
        """
        backup_file = open("database/"+self.database_name+".txt",'w',encoding="utf8")
        backup_file.write(json.dumps(self.data_list))
        backup_file.close()
        self.write_bkup_database()

    def add_user(self, user_name:str):
        """
        Creates a basic template profile for a user using their username.
        Writes and backsup database.
        """
        now = datetime.datetime.now()
        
        temp_profile = '{"'+user_name+'":{"discord_id":"'+user_name+'","nickname":"'+user_name.split("#",1)[0]+'","weight":0,"height":0,"bmi_result":"None","gender":"None","bmi":0,"reminders":{},"log_history":{"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'":{"push_ups":0,"calorie_intake":0,"situps":0,"miles":0,"calories_lost":0,"log":"Entry text..."}},"age":0}}'
        json_dictionary = json.loads(temp_profile)

        self.data_list["users"].update(json_dictionary)

        self.write_json_database()
        self.write_bkup_database()

    def remove_user(self, user_name:str):
        """
        Removes a user from the database using their username.
        Writes and backsup database.
        """
        del self.data_list["users"][user_name]
        self.write_json_database()
        self.write_bkup_database()

if __name__ == '__main__':
    bot = Database("accounts")
    bot.load_json_database()
    bot.add_user("Jeff")
    bot.add_user("CJ")
    bot.remove_user("Jeff")
