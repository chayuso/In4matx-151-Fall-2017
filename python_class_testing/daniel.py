#Test Class
from database import Database
import json

class Test():
    def __init__(self,database):
        self.string = ""
        self.database = database
        self.workout_dict = {"excercise": None, "reps": None, "sets": None, "weight": None}
        self.workout_list = []
        self.workout_counter = 0
        

        
    def record_workout(self):
        self.workout_list.append(self.workout_dict)
        self.workout_counter += 1
        print("Workout " + str(self.workout_counter) +" added to list")
        print(self.workout_list)
        self.workout_dict = {"excercise": None, "reps": None, "sets": None, "weight": None}
        return self.workout_list


        
    
    def add_excercise(self, excercise):
        self.workout_dict["excercise"] = excercise
        
    def add_weight(self, weight):
        self.workout_dict["weight"] = weight 
        print("Logged " + str(weight) + " pounds to " + self.workout_dict["excercise"] + " workout")
        
    def add_sets(self, sets):
        self.workout_dict["sets"] = sets 
        print("Logged " + str(sets) + " sets to " + self.workout_dict["excercise"] + " workout")

    def add_reps(self, reps):
        self.workout_dict["reps"] = reps
        print("Logged " + str(reps) + " reps to " + self.workout_dict["excercise"] + " workout")

    def log_workout(self, username):
            
        for k,v in database_object.data_list.items(): #users dict
            if type(v) is dict:
                for user,userinfo in v.items(): #userinfo type dict
                    for item in userinfo["log_history"]:
                        for i in item:
                            if i == "log" and user == username:
                                print("Logging workout for: ", user)
                                if self.record_workout() not in database_object.data_list["users"][username]["log_history"]:
                                    database_object.data_list["users"][username]["log_history"].append(self.record_workout())
                                
    def print_json(self): #Kenny's code 
        pretty = (self.database.data_list)
        print(json.dumps(pretty,indent=3))
                        

if __name__ == '__main__':
    database_object = Database("accounts")
    database_object.load_json_database()
    database_object.add_user("Danienl1", str(408))
    
    
    bot = Test(database_object)
    
    
    bot.add_excercise("Bench Press")
    bot.add_reps(10)
    bot.add_sets(3)
    bot.add_weight(150)
    bot.log_workout("Danienl1")
    print()
    
    bot.add_excercise("Chest Press")
    bot.add_reps(8)
    bot.add_sets(4)
    bot.add_weight(150)
    bot.log_workout("Danienl1")
    print()
    
    
        
    bot.add_excercise("Legs")
    bot.add_reps(8)
    bot.add_sets(4)
    bot.add_weight(150)
    bot.log_workout("Danienl1")
    print()
    
    bot.print_json()
    
