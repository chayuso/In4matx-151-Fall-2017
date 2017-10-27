import json
from pytz import timezone
from datetime import datetime, timedelta
import json
import plotly
import plotly.plotly as py
from plotly.graph_objs import *
from pytz import timezone

plotly.tools.set_credentials_file(username='kmatsudo', api_key='En9O6dgqc7dXPsKdL2EY')

class Database():
    def __init__(self,database_file_name:str):
        """
        Requires the name of the database file located under /database
        directory.
        """
        self.data_list = {}
        self.database_name = database_file_name
        self.load_json_database()

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
        now = datetime.now(timezone('US/Pacific'))
        
        temp_profile = '{"'+user_name+'":{"discord_username":"'+user_name+'","discord_id":"'+user_id+'","nickname":"'+user_name.split("#",1)[0]+'","weight":0,"height":0,"bmi_result":"None","gender":"None","bmi":0,"reminders":[],"log_history":[{"calorie_intake":0,"calories_lost":0,"situps":0,"weight":0,"miles":0,"log":"Entry text...","push_ups":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}],"age":0}}'
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

    def user_reminders(self,username:str):
        """
        Returns string of user reminders.
        """
        return_string="Reminder List for user "+username+":\n"
        index = 1
        for reminder in self.data_list["users"][username]["reminders"]:
            return_string+="\nReminder #"+str(index)+":\n    name: "+reminder["reminder_name"]+"\n    date: "+reminder["reminder_date"]+"\n    time: "+reminder["reminder_time"]
            index+=1
        return return_string

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

    def print_pacific_time(self):
        print(datetime.now(timezone('US/Pacific')))

class Plotter():
    def __init__(self,database):
        
        self.local_database = database

    def print_json(self):
        pretty = (self.local_database.data_list)
        print(json.dumps(pretty,indent=3))

    def get_category_by_date(self,username:str,category:str,date:str):
        """
        Compatible with
            "weight"
            "miles"
            "calorie_intake"
            "calories_lost"
            "push_ups"
            "situps"
        """
        for log in self.local_database.data_list["users"][username]["log_history"]:
            if date == log["date"]:
                return log[category]
        return "Category not found for date!"

    def get_log_by_date(self,username,date):
        for log in self.local_database.data_list["users"][username]["log_history"]:
            if log["date"]==date:
                return log
        return None 

    def set_category_today(self,username:str,category:str,value:int,test_mode=False,test_increment=0):
        """
        Compatible with
            "weight"
            "miles"
            "calorie_intake"
            "calories_lost"
            "push_ups"
            "situps"
        """
        last_log = self.local_database.data_list["users"][username]["log_history"][-1]
        if test_mode: #testmode manually adds weight on incremented day
            now = datetime.now(timezone('US/Pacific'))
            now += timedelta(days=test_increment)
            last_date = datetime.strptime(last_log["date"].replace("/","-"), '%m-%d-%Y')
            if now.date()>last_date.date():
                temp_log = '{"calorie_intake":0,"calories_lost":0,"situps":0,"weight":0,"miles":0,"log":"Entry text...","push_ups":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}'
                json_dictionary = json.loads(temp_log)
                json_dictionary[category] = value
                self.local_database.data_list["users"][username]["log_history"].append(json_dictionary)
            else:
                print("Don't add a previous day, creates out of order dates in list")
        elif last_log["date"] == str(datetime.today().month)+"/"+str(datetime.today().day)+"/"+str(datetime.today().year):
            last_log[category] = value
        else:
            now = datetime.now(timezone('US/Pacific'))
            temp_log = '{"calorie_intake":0,"calories_lost":0,"situps":0,"weight":0,"miles":0,"log":"Entry text...","push_ups":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}'
            json_dictionary = json.loads(temp_log)
            json_dictionary[category] = value
            self.local_database.data_list["users"][username]["log_history"].append(json_dictionary)

        self.local_database.write_json_database()
        self.local_database.write_bkup_database()
    
    def generate_chart(self,username:str, category:str,most_recent:int,test_num=0):
        #test_num increments day of testing if added dates up to 86
        #program will think to test up from most_recent until the tested increment
        """
        Compatible with
            "weight"
            "miles"
            "calorie_intake"
            "calories_lost"
            "push_ups"
            "situps"
        """
        date_list = []
        weight_list = []
        check_date = datetime.today()-timedelta(days=most_recent)+timedelta(days=test_num)
        last_weight = 0
        
        for i in range(0,most_recent+1):
            check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
            log_entry = self.get_log_by_date(username,check_string)
            if log_entry and log_entry[category]!=0 and category in log_entry.keys():
                date_list.append(log_entry["date"])
                weight_list.append(log_entry[category])
                last_weight = log_entry[category]
            else:
                if last_weight != 0:
                    date_list.append(check_string)
                    weight_list.append(last_weight)
            check_date += timedelta(days=1)
        if not date_list:
            return "Empty List"
        py.image.save_as({
            "data": [Scatter(x=date_list, y=weight_list)],
            "layout": Layout(title=category.title()+"Graph")
        },filename="plot_graphs/"+username+"_"+category+"_graph.png")
