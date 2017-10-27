from database import Database
from datetime import datetime, timedelta
import json
import plotly
import plotly.plotly as py
from plotly.graph_objs import *
from pytz import timezone

plotly.tools.set_credentials_file(username='kmatsudo', api_key='En9O6dgqc7dXPsKdL2EY')



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
        
        for i in range(0,most_recent):
            check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
            log_entry = self.get_log_by_date(username,check_string)
            if log_entry and log_entry[category]!=0:
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

        plotly.offline.plot({
            "data": [Scatter(x=date_list, y=weight_list)],
            "layout": Layout(title=category.title()+"Graph")
        },filename="plot_graphs/"+username+"_"+category+"_graph.html",auto_open=False)
        return "Chart Generated"
    
if __name__ == "__main__":
    heller = Plotter(Database("accounts"))
    #NOTE! USE last two parameters for testing even if adding
    #current date with 0. Bot should be the only one automatically
    #setting weights daily.

    #Was first tested with "weight" category, then switched to situps to
    #Check Compatability
    heller.local_database.add_user("CJ","238420205104136203")#Resets CJ User even if already in database
    heller.set_category_today("CJ","situps",150)
    heller.set_category_today("CJ","situps",156,True,3)
    heller.set_category_today("CJ","situps",170,True,10)
    heller.set_category_today("CJ","situps",160,True,15)
    heller.set_category_today("CJ","situps",165,True,53)
    heller.set_category_today("CJ","situps",155,True,63)
    heller.set_category_today("CJ","situps",148,True,73)
    heller.set_category_today("CJ","situps",160,True,76)
    heller.set_category_today("CJ","situps",163,True,84)
    heller.set_category_today("CJ","situps",180,True,86)

    heller.print_json()
    print(heller.generate_chart("CJ","situps",100,86))
    print(heller.generate_chart("chayuso#5309","situps",100))
    print(heller.get_category_by_date("CJ","situps","10/26/2017"))


