#Test Class
from database import Database

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
                                self.record_workout()
                                
                        

if __name__ == '__main__':
    database_object = Database("accounts")
    database_object.load_json_database()
    
    
    bot = Test(database_object)
    
    bot.add_excercise("Bench Press")
    bot.add_reps(10)
    bot.add_sets(3)
    bot.add_weight(150)

    #print(bot.workout_dict)
    
    bot.log_workout("daniel")
    print()
    
    bot.add_excercise("Chest Press")
    bot.add_reps(8)
    bot.add_sets(4)
    bot.add_weight(150)
    
    
    bot.log_workout("daniel")
    print()
    

