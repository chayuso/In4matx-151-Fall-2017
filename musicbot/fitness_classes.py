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
        return_string=" "
        index = 1
        for reminder in self.data_list["users"][username]["reminders"]:
            return_string+="Reminder #"+str(index)+":\n        name: "+reminder["reminder_name"]+"\n        date: "+reminder["reminder_date"]+"\n        time: "+reminder["reminder_time"]+"\n"
            index+=1
        if return_string == " ":
            return '    **-No pending reminders! Add with "+" emoji**'
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
        
class BMI_Calculator():
    def __init__(self,database):
        ## Keeps creating a new instance of "Kenny" instead of adding on to it
        self.local_database = database
        
############ GENERAL FUNCTIONS ############
    #------ Weight ------# 

    def get_weight(self,name):
        #print(self.local_database.data_list["users"][name]["weight"])
        return(self.local_database.data_list["users"][name]["weight"])

    def set_weight(self,name,weight):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["weight"] = weight
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()
        

     #------ Height ------# 
               

    def get_height(self,name):
        #print(self.local_database.data_list["users"][name]["height"])
        return(self.local_database.data_list["users"][name]["height"])


    def set_height(self,name,height):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["height"] = height
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()

        
    #------ Gender ------# 

    def get_gender(self,name):
        #print(self.local_database.data_list["users"][name]["gender"])
        return(self.local_database.data_list["users"][name]["gender"])

    
    def set_gender(self,name,gender):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["gender"] = gender
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()


    #------ Age ------# 


    def get_age(self,name):
        #print(self.local_database.data_list["users"][name]["age"])
        return(self.local_database.data_list["users"][name]["age"])

    
    def set_age(self,name,age):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["age"] = age
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()

        
    #------ BMI ------# 

    # Gets the weight and height from the profile and calculates BMI.

    def get_bmi(self,name):

        weight = float(self.get_weight(name))
        if weight == 0:
            return -1
        # Spits the height (its a string) into an array[0] = ft , array[1] = inches
        try:
            self.get_height(name).split("'")
        except:
            return 0
        
        string_height = self.get_height(name).split("'")
        ft_in_inches = int(string_height[0]) * 12
        total_height = ft_in_inches + int(string_height[1])

        bmi = ( weight / (total_height * total_height)) * 703
        print("BMI: " + str(bmi))
        return bmi
    
class Exercise_Recorder():
    def __init__(self,database):
        self.local_database = database

    def reset_routines_list(self):
        self.local_database.data_list["users"][username]["routine_list"] = []
        temp_e = '{"name":"Chest","exercises": [{"exercise_name": "Bench","sets": []},{"exercise_name": "Incline Bench","sets": []},{"exercise_name": "Incline Dumbbell Press","sets": []},{"exercise_name": "Fly Machine","sets": []}]}'
        json_dictionary = json.loads(temp_e)
        self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
        temp_e = '{"name":"Back","exercises":[{"exercise_name":"Deadlift","sets":[]},{"exercise_name":"T-Bar Rows","sets":[]},{"exercise_name":"Lat Pulldowns","sets":[]},{"exercise_name":"Single-Arm Bent-Over Rows","sets":[]}]}'
        json_dictionary = json.loads(temp_e)
        self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
        temp_e = '{"name":"Legs","exercises":[{"exercise_name":"Squats","sets":[]},{"exercise_name":"Leg Press","sets":[]},{"exercise_name":"Leg Extension","sets":[]},{"exercise_name":"Leg Curls","sets":[]}]}'
        json_dictionary = json.loads(temp_e)
        self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
        temp_e = '{"name":"Shoulders","exercises":[{"exercise_name":"Seated Military Press","sets":[]},{"exercise_name":"Arnold Press","sets":[]},{"exercise_name":"Front Raise","sets":[]},{"exercise_name":"Seated Reverse Flys","sets":[]},{"exercise_name":"Lateral Raise","sets":[]}]}'
        json_dictionary = json.loads(temp_e)
        self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)

    def create_default_routines(self, username:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            self.local_database.data_list["users"][username]["routine_list"] = []
            temp_e = '{"name":"Chest","exercises": [{"exercise_name": "Bench","sets": []},{"exercise_name": "Incline Bench","sets": []},{"exercise_name": "Incline Dumbbell Press","sets": []},{"exercise_name": "Fly Machine","sets": []}]}'
            json_dictionary = json.loads(temp_e)
            self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
            temp_e = '{"name":"Back","exercises":[{"exercise_name":"Deadlift","sets":[]},{"exercise_name":"T-Bar Rows","sets":[]},{"exercise_name":"Lat Pulldowns","sets":[]},{"exercise_name":"Single-Arm Bent-Over Rows","sets":[]}]}'
            json_dictionary = json.loads(temp_e)
            self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
            temp_e = '{"name":"Legs","exercises":[{"exercise_name":"Squats","sets":[]},{"exercise_name":"Leg Press","sets":[]},{"exercise_name":"Leg Extension","sets":[]},{"exercise_name":"Leg Curls","sets":[]}]}'
            json_dictionary = json.loads(temp_e)
            self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
            temp_e = '{"name":"Shoulders","exercises":[{"exercise_name":"Seated Military Press","sets":[]},{"exercise_name":"Arnold Press","sets":[]},{"exercise_name":"Front Raise","sets":[]},{"exercise_name":"Seated Reverse Flys","sets":[]},{"exercise_name":"Lateral Raise","sets":[]}]}'
            json_dictionary = json.loads(temp_e)
            self.local_database.data_list["users"][username]["routine_list"].append(json_dictionary)
            
    def routine_menu_string(self, username:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            self.create_default_routines(username)
        return_string = ""
        r_num = 1
        for r in self.local_database.data_list["users"][username]["routine_list"]:
            return_string+="Routine #"+str(r_num)+"- "+r["name"]+"\n"
            r_num+=1
        return return_string
    
    def get_exercise_name_by_int(self, username:str,routine:str, num:int):
        for r in self.local_database.data_list["users"][username]["routine_list"]:
            if r["name"]== routine:
                return r["exercises"][num]["exercise_name"]
        return None
        
    def exercise_menu_string(self, username:str,routine:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            self.create_default_routines(username)
        return_string = "__**Routine**__ - "+routine+"\n"
        for r in self.local_database.data_list["users"][username]["routine_list"]:
            if r["name"]== routine:
                e_num = 1
                if len(r["exercises"]) == 0:
                    return_string+="        No exercises inputed. Add Exercises."
                for e in r["exercises"]:
                    return_string+="    Exercise #"+str(e_num)+"- "+e["exercise_name"]+"\n"
                    e_num+=1
        return return_string
    
    def set_menu_string(self, username:str,routine:str,exercise:str):
        last_log = self.local_database.data_list["users"][username]["log_history"][-1]
        now = datetime.now(timezone('US/Pacific'))
        if last_log["date"] == str(now.month)+'/'+str(now.day)+'/'+str(now.year):
            if "routines" not in last_log:
                return_string = "__**Routine**__ - "+routine+"\n"+"    __**Exercise**__ - "+exercise+"\n"
                for r in self.local_database.data_list["users"][username]["routine_list"]:
                    if r["name"]== routine:
                        for e in r["exercises"]:
                            if e["exercise_name"]== exercise:
                                s_num = 1
                                if len(e["sets"]) == 0:
                                    return_string+="        No sets inputed. Add Sets."
                                for s in e["sets"]:
                                    return_string+="        Set #"+str(s_num)+"- Reps: "+str(s["reps"])+", Weight: "+str(s["weight"])+"\n"
                                    s_num+=1
                return return_string
            return_string = "__**Routine**__ - "+routine+"\n"+"    __**Exercise**__ - "+exercise+"\n"

            for r in last_log["routines"]:
                if r["name"]== routine:
                    for e in r["exercises"]:
                        if e["exercise_name"]== exercise:
                            s_num = 1
                            if len(e["sets"]) == 0:
                                return_string+="        No sets inputed. Add Sets."
                            for s in e["sets"]:
                                return_string+="        Set #"+str(s_num)+"- Reps: "+str(s["reps"])+", Weight: "+str(s["weight"])+"\n"
                                s_num+=1
            return return_string
            
        else:
            return_string = "__**Routine**__ - "+routine+"\n"+"    __**Exercise**__ - "+exercise+"\n"
            for r in self.local_database.data_list["users"][username]["routine_list"]:
                if r["name"]== routine:
                    for e in r["exercises"]:
                        if e["exercise_name"]== exercise:
                            s_num = 1
                            if len(e["sets"]) == 0:
                                return_string+="        No sets inputed for today. Add Sets."
                            for s in e["sets"]:
                                return_string+="        Set #"+str(s_num)+"- Reps: "+str(s["reps"])+", Weight: "+str(s["weight"])+"\n"
                                s_num+=1
            return return_string
    
    def routines_today_string(self, username:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            self.create_default_routines(username)
        last_log = self.local_database.data_list["users"][username]["log_history"][-1]
        now = datetime.now(timezone('US/Pacific'))
        if last_log["date"] == str(now.month)+'/'+str(now.day)+'/'+str(now.year):
            if "routines" not in last_log:
                return " "
            return_string = ""
            r_num = 1
            for r in last_log["routines"]:
                return_string+="Routine #"+str(r_num)+"- "+r["name"]+"\n"
                e_num = 1
                for e in r["exercises"]:
                    if len(e["sets"]) !=0:
                        return_string+="    Exercise #"+str(e_num)+"- "+e["exercise_name"]+"\n"
                        s_num = 1
                        for s in e["sets"]:
                            return_string+="        Set #"+str(s_num)+"- Reps: "+str(s["reps"])+", Weight: "+str(s["weight"])+"\n"
                            s_num+=1
                        e_num+=1
                r_num+=1
            return return_string
            
        else:
            return " "
        
    def add_routine(self, username:str, routine:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            self.create_default_routines(username)
        else:
            for i in self.local_database.data_list["users"][username]["routine_list"]:
                if i["name"]==routine:
                    return 1
        temp_routine = {"name": routine, "exercises": []}
        self.local_database.data_list["users"][username]["routine_list"].append(temp_routine)
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()

    def get_routine(self, username:str, routine:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            return None
        else:
            for i in self.local_database.data_list["users"][username]["routine_list"]:
                if i["name"]==routine:
                    return i
        return None
        
    def add_excercise_to_routine(self, username:str, routine:str,exercise:str):
        if "routine_list" not in self.local_database.data_list["users"][username]:
            return 1
        else:
            temp_ex = {"exercise_name": exercise,"sets": []}
            for r in self.local_database.data_list["users"][username]["routine_list"]:
                if r["name"]==routine:
                    for e in r["exercises"]:
                        if e["exercise_name"] == exercise:
                            return -2
                    r["exercises"].append(temp_ex)
                    self.local_database.write_json_database()
                    self.local_database.write_bkup_database()
                    return 0
            self.add_routine(username,routine)
            self.add_excercise(username, routine,exercise,sets)
            return -1
        
    def set_excercise_reps_weight_today(self, username:str, routine:str,exercise:str,reps:int,weight:int):
        last_log = self.local_database.data_list["users"][username]["log_history"][-1]
        now = datetime.now(timezone('US/Pacific'))
        if last_log["date"] == str(now.month)+'/'+str(now.day)+'/'+str(now.year):
            if "routines" not in last_log:
                last_log["routines"] = []
            if self.get_routine(username, routine):
                for r in last_log["routines"]:
                    if r["name"]==routine:
                        for e in r["exercises"]:
                            if e["exercise_name"]==exercise:
                                e["sets"].append({"reps":int(reps),"weight":int(weight)})
            else:
                return 1
        else:
            temp_log = '{"calorie_intake":0,"calorie_burn":0,"miles":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}'
            json_dictionary = json.loads(temp_log)
            json_dictionary["routines"] = []
            if self.get_routine(username, routine):
                json_dictionary["routines"].append(self.get_routine(username, routine))
                for r in json_dictionary["routines"]:
                    if r["name"]==routine:
                        for e in r["exercises"]:
                            if e["exercise_name"]==exercise:
                                e["sets"].append({"reps":int(reps),"weight":int(weight)})
            else:
                return 1
            self.local_database.data_list["users"][username]["log_history"].append(json_dictionary)
            
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()
        
    def add_routine_today(self,username:str,routine:str):
        last_log = self.local_database.data_list["users"][username]["log_history"][-1]
        now = datetime.now(timezone('US/Pacific'))
        if last_log["date"] == str(now.month)+'/'+str(now.day)+'/'+str(now.year):
            if "routines" not in last_log:
                last_log["routines"] = []
            if self.get_routine(username, routine):
                for r in last_log["routines"]:
                    if r["name"] == routine:
                        return -1
                last_log["routines"].append(self.get_routine(username, routine))
            else:
                return 1
        else:
            temp_log = '{"calorie_intake":0,"calorie_burn":0,"miles":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}'
            json_dictionary = json.loads(temp_log)
            json_dictionary["routines"] = []
            if self.get_routine(username, routine):
                json_dictionary["routines"].append(self.get_routine(username, routine))
            else:
                return 1
            self.local_database.data_list["users"][username]["log_history"].append(json_dictionary)
            
        self.local_database.write_json_database()
        self.local_database.write_bkup_database()
        
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
    
    def get_last_log_string(self,username,date:str):
        latest_log = self.get_log_by_date(username,date)
        return_string = ""
        return_string+="Date: "+str(date)+"\n"
        for key in latest_log:
            if key!="routines" and key!="date" and key!="log" :
                if latest_log[key]!=0:
                    return_string+="    "+str(key)+": "+str(latest_log[key])+"\n"
        return return_string
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
        now = datetime.now(timezone('US/Pacific'))
        if last_log["date"] == str(now.month)+'/'+str(now.day)+'/'+str(now.year):
            last_log[category] = value
        else:
            temp_log = '{"calorie_intake":0,"calorie_burn":0,"miles":0,"date":"'+str(now.month)+'/'+str(now.day)+'/'+str(now.year)+'"}'
            json_dictionary = json.loads(temp_log)
            json_dictionary[category] = value
            self.local_database.data_list["users"][username]["log_history"].append(json_dictionary)

        self.local_database.write_json_database()
        self.local_database.write_bkup_database()
        
    def get_log_history_string(self,username:str,most_recent:int):
        return_string = "__**Log History:**__\n"
        date_list = []
        check_date = datetime.now(timezone('US/Pacific'))-timedelta(days=most_recent)
        n = 1
        for i in range(0,most_recent+1):
            check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
            log_entry = self.get_log_by_date(username,check_string)
            if log_entry:
                return_string += "Log #"+str(n)+":\n"
                n+=1
                date_list.append(log_entry["date"])
                return_string +=self.get_last_log_string(username,check_string)+"\n"+self.routines_today_string(username,check_string)+"__________\n"
            check_date += timedelta(days=1)
        if not date_list:
            return "No log history for past "+str(most_recent)+" days"
        return return_string

    def routines_today_string(self,username:str,date:str):
        last_log = self.get_log_by_date(username,date)
        if "routines" not in last_log:
            return " "
        return_string = " "
        r_num = 1
        for r in last_log["routines"]:
            return_string+="Routine #"+str(r_num)+"- "+r["name"]+"\n"
            e_num = 1
            for e in r["exercises"]:
                if len(e["sets"]) !=0:
                    return_string+="    Exercise #"+str(e_num)+"- "+e["exercise_name"]+"\n"
                    s_num = 1
                    for s in e["sets"]:
                        return_string+="        Set #"+str(s_num)+"- Reps: "+str(s["reps"])+", Weight: "+str(s["weight"])+"\n"
                        s_num+=1
                    e_num+=1
            r_num+=1
        return return_string    
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
        check_date = datetime.now(timezone('US/Pacific'))-timedelta(days=most_recent)+timedelta(days=test_num)
        last_weight = 0
        
        for i in range(0,most_recent+1):
            check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
            log_entry = self.get_log_by_date(username,check_string)
            if log_entry and category in log_entry.keys() and log_entry[category]!=0:
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
