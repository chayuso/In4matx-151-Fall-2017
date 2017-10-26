#Test Class
from database import Database

class Test():
    def __init__(self,database):
        self.string = ""
        self.database = database
        self.workout_dict = {"excercise": None, "reps": None, "sets": None, "weight": None}
        self.workout_list = []


    def print_age(self,username):
        print(self.database.data_list["users"][username]["age"])
        
        
    def record_workout(self, workout_dict, workout):
        pass
    
    def add_excercise(self, excercise):
        self.workout_dict["excercise"] = excercise
        print(self.workout_dict)
        
    def add_weight(self, weight):
        self.workout_dict["weight"] = weight 
        print("Logged " + str(weight) + " pounds to this workout")
        
    def add_sets(self, sets):
        self.workout_dict["sets"] = sets 
        print("Logged " + str(sets) + " sets to this workout")

    def add_reps(self, reps):
        self.workout_dict["reps"] = reps
        print("Logged " + str(reps) + " reps to this workout")


if __name__ == '__main__':
    database_object = Database("accounts")
    database_object.load_json_database()
    
    
    bot = Test(database_object)
    
    bot.add_excercise("Bench Press")
    bot.add_reps(10)
    bot.add_sets(3)
    bot.add_weight(150)
    print()
    for k in bot.workout_dict.items():
        print(k)

    print()
    print(bot.workout_dict)

    
    for k,v in database_object.data_list.items(): #users dict
        if type(v) is dict:
            for user,userinfo in v.items(): #userinfo type dict
                for item in userinfo["log_history"]:
                    for i in item:
                        if i == "log" and user == "Daniel":
                            print("hi")
                        
                        
                
#                if user == "Daniel":
 ##                      if item == "log_history":
   #                         print(userinfo)


    
