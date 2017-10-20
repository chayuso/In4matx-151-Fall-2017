import json
import datetime

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

    def add_user(self, user_name:str, user_id:str):
        """
        Creates a basic template profile for a user using their username.
        Writes and backsup database.
        """
        now = datetime.datetime.now()
        
        temp_profile = '{"'+user_name+'":{"discord_username":"'+user_name+'","discord_id":"'+user_id+'","nickname":"'+user_name.split("#",1)[0]+'","weight":0,"height":0,"bmi_result":"None","gender":"None","bmi":0,"reminders":[],"log_history":[{"calorie_intake":0,"calories_lost":0,"situps":0,"miles":0,"log":"Entry text...","push_ups":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}],"age":0}}'
        json_dictionary = json.loads(temp_profile)

        self.data_list["users"].update(json_dictionary)

        self.write_json_database()
        self.write_bkup_database()
        return 'User "'+user_name+'" added!'

    def remove_user(self, user_name:str):
        """
        Removes a user from the database using their username.
        Writes and backsup database.
        """
        del self.data_list["users"][user_name]
        self.write_json_database()
        self.write_bkup_database()
        return 'User "'+user_name+'" removed!'

    def add_reminder(self, username:str,date:str, hour:str, minute:str,reminder:str):
        """
        Add a reminder note to database based on user.
        """
        R = {"reminder_name":reminder,"reminder_date":date,"reminder_time":hour+':'+minute}
        self.data_list["users"][username]["reminders"].append(R)

        self.write_json_database()
        self.write_bkup_database()
        return "Reminder added!"

    def remove_reminder(self, username:str,entry:int):
        """
        Removes entry by date or entry number
        """
        try:
            del self.data_list["users"][username]["reminders"][entry]
        except:
            print("Entry index not valid.")
            return "Invalid index"

        self.write_json_database()
        self.write_bkup_database()
        return "Reminder removed!"

    def print_database(self):
        print("Printing Database...\n################################################\n"+json.dumps(self.data_list,indent=4, sort_keys=True)+"\n################################################")
