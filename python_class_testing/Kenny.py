from database import Database
import json
import plotly
import plotly.plotly as py
from plotly.graph_objs import *

plotly.tools.set_credentials_file(username='kmatsudo', api_key='En9O6dgqc7dXPsKdL2EY')



class Prototype:
    def __init__(self):
        ## Keeps creating a new instance of "Kenny" instead of adding on to it
        self.local_database = Database("accounts")
        self.local_database.load_json_database()
        self.local_database.add_user("kenny",str(4056));
        self.local_database.add_reminder("kenny","tuesday","10","44","Work on project")

############ GENERAL FUNCTIONS ############

    def print_json(self):
        pretty = (self.local_database.data_list)
        print(json.dumps(pretty,indent=3))
        
    #------ Weight ------# 


    def get_weight(self,name):
        #print(self.local_database.data_list["users"][name]["weight"])
        return(self.local_database.data_list["users"][name]["weight"])

    def set_weight(self,name,weight):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["weight"] = weight
        

     #------ Height ------# 
               

    def get_height(self,name):
        #print(self.local_database.data_list["users"][name]["height"])
        return(self.local_database.data_list["users"][name]["height"])


    def set_height(self,name,height):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["height"] = height

        
    #------ Gender ------# 

    def get_gender(self,name):
        #print(self.local_database.data_list["users"][name]["gender"])
        return(self.local_database.data_list["users"][name]["gender"])

    
    def set_gender(self,name,gender):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["gender"] = gender


    #------ Age ------# 


    def get_age(self,name):
        #print(self.local_database.data_list["users"][name]["age"])
        return(self.local_database.data_list["users"][name]["age"])

    
    def set_age(self,name,age):
        #gets current height (only gets weight from log_history"
        self.local_database.data_list["users"][name]["age"] = age

        
    #------ BMI ------# 

    # Gets the weight and height from the profile and calculates BMI.

    def get_bmi(self,name):

        weight = int(self.get_weight(name))
        # Spits the height (its a string) into an array[0] = ft , array[1] = inches
        string_height = self.get_height(name).split("'")
        ft_in_inches = int(string_height[0]) * 12
        total_height = ft_in_inches + int(string_height[1])

        bmi = ( weight / (total_height * total_height)) * 703
        print("BMI: " + str(bmi))
        return bmi

        
    
    ############ LOG HISTORY FUNCTIONS ############
        
    def set_log(self,name,attribute,value):
        #sets the latest log entry's attribute to a value.
        #example, set_log("kenny","weight",1000000)  
        self.local_database.data_list["users"][name]["log_history"][0][attribute] = value
        if attribute == "weight":
            self.set_weight(name,value)
        if attribute == "height":
            self.set_height(name,value)
            

    
        
        

    
     
if __name__ == "__main__":
    #starts class
    heller = Prototype()
    
#    sets attributes in log_history
    heller.set_log("kenny","miles",2)
    heller.set_log("kenny","weight",150)
    heller.set_log("kenny","height","5'6")
    heller.set_log("kenny","situps",100)
    heller.set_log("kenny","calorie_intake",3000)
    heller.set_log("kenny","log","Today I am hungry!")

    heller.print_json()

    heller.set_gender("kenny","unknown")
    heller.get_gender("kenny")

    heller.get_bmi("kenny")

    
    plotly.offline.plot({
            "data": [Scatter(x=[1,2,3,4,5,6,7,8,9,10], y=[150,148,151,149,150,150,150,151,152,153,180])],
            "layout": Layout(title="WeightGraph")
        },auto_open=False)

