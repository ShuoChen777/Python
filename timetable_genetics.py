from flask import Flask, render_template, url_for, redirect, request
from cs50 import SQL
import random
import math

db = SQL("sqlite:///database.db")

#global arrays, can be changed by user input or otherwise
school_days = []
periods = 0
period_list = []
grades = 0
iterations = 1000
subjects = [0] #provides the list of subjects. '0' symbolises a 'free' period
ranked_subject_arrays = [] #this array will store our rankings
block_content = [] #this array stores which subjects are in which block


# checking the amount of subjects that should be included
def subject_fitness(array_content):
    #In this fitness function: 
    # x should be the master array
    # It will check the relationship between the average desired number of subjects and the actual number of subjects per week.
    total = 0
    for grade in range(0, grades):
        x = []
        for i in range(0, len(subjects)):
            x.append(0)
            for day in range(0, len(school_days)):
                x[i] += array_content[grade][day][i]
        
        for i in range(0, len(subjects)):
            total = total + abs(x[i] - subject_set[i])
                
    return total

# setting up the condition for one of the fitness functions        
def condition_construct(grades):
    #clash condition construction creation carnival
    if grades >= 2:
        condition = "where (grade_0 = grade_1 and not (grade_0 = -1 or grade_1 = -1))"

        #here, the condition is altered to increase in length according to the number of grades present
        for i in range(0, (grades - 2)):
            for j in range(i, (grades - 1)):
                temp_grade1 = str("grade_" + str(j))
                temp_grade2 = str("grade_" + str((grades - (i + 1))))
                condition = str(condition + " or (" + temp_grade1 + " = " + temp_grade2 + " and not (" + temp_grade1 + " = -1 or " + temp_grade2 + " = -1))")

    else:
        condition = "where (0 = 1)"
    return condition

# creates an error database for locating the location of errors
def construct_errors(array_content, d, grades, condition):

    error_db = str(d + "_error")

    db.execute("update ? set 'clash' = 0;", error_db)
    db.execute("update ? set 'overlap' = 0;", error_db)
    
    xcondition = str("select period from " + d + " " + condition + ";")
    
    # Locating clashes between subjects
    x = db.execute(xcondition)
    for i in range(0, len(x)):
        db.execute("update ? set 'clash' = 1 where period = ?;", error_db, str(x[i]["period"]))

    # Locating overlaps over recesses
    for i in range(0, grades):
        for j in range(0, (len(array_content[i]) - 1)):
            for k in range(0, len(period_list) - 1):
                if ((array_content[i][j] != 0) and (j == (period_list[k] - 1))):
                    if array_content[i][j] == array_content[i][j+1]:
                        db.execute("update ? set 'overlap' = 1 where period = ?;", error_db, str((j + 1)))
                        db.execute("update ? set 'overlap' = 1 where period = ?;", error_db, str((j + 2)))

# fitness function, validates the actual timetable
def construct_fitness(array_content, array_length, d, grades, condition):

    error_db = str(d + "_error")
    
    #In this fitness function:
    # x refers to the clashes between grades
    # y refers to the overlaps across break times
    # z refers to the amount of extra or missing periods

    x = len(db.execute("select period from ? where 'clash' = 1;", error_db))
    y = len(db.execute("select period from ? where 'overlap' = 1;", error_db))
    z = 0

    for i in range(0, grades):
        z += abs(len(array_content[i]) - array_length)

    fit = 5*x + 1*y + 1*z


    return [fit]
            
    #The fitness function should check the following:
    
    #- Clashes. Grade 2 cannot have subject A if Grade 1 is also having subject A at the same time.
    #- Overlaps. A double session should not extend through 'breaks' or 'lunch' times.
    #- Missing/extra. Sometimes, the program might lead to some days having more or less subjects than expected.

# helps to log error locations into temporary arrays later in the program
def error_log(main_array, error_array, limit):
    for i in range(0, len(error_array)):
        temp = error_array[i]["period"] - 1
        if (temp < limit):
            main_array[temp] = 1

    return main_array


def timetable_init():

    #from the 'recess.html' file, we extract the data about recess periods and append them to a global array.
    # all variables that will be used in the mutation subroutine later is globalised.
    global clash_condition, ranked_subject_arrays, period_list, subjects, subject_set

    groups = int(db.execute("select block from school where id = 0;")[0]["block"])
    period_list = []

    for i in range(1, periods):
        if str(request.form.get(str(i))) != "None":
            period_list.append(i)
    period_list.append(periods)

    #adding the groups onto the array...
    for i in range(0, groups):
        subjects.append((i + 1))


    # Number of subjects for each year group should be even. subject A should have the same quantity as subject B per week.
    # minimise free periods. Free periods may stay as single subjects. Can be placed anywhere.

    #this variable defines that there should be this many of each subject per week for a given grade.
    subject_count = math.floor((len(school_days) * periods) / (len(subjects) - 1))

    # the condition for the clashes between subjects is declared here
    
    clash_condition = condition_construct(grades)

    #this function here assigns how many repetitions of each subject will be present.
    #the number of 'free' periods is determined by the subject_count variable.
    subject_set = [(len(school_days) * periods) - (subject_count * (len(subjects) - 1))]
    for _ in range(0, len(subjects) - 1):
        subject_set.append(subject_count)

    #it'll some iterations here
    for iteration in range(iterations):
    #determine how many of each subject will be present for each school day.
    #initialise 3d array to store how many of each subject will be there per day, per grade.
    #also apply free subjects to this array on initialisation.
        master_subject_array = []

        for i in range(0, grades):
            temp_subject_array = []
            for _ in range(0, len(school_days)):
                temp_subject_array.append([0, 0, 0, 0, 0, 0, 0])
            #This randomly chooses which days get the free periods.
            for _ in range(0, subject_set[0]):
                temp_subject_array[random.randint(0, len(school_days) - 1)][0] += 1
            master_subject_array.append(temp_subject_array)


        #adding subjects (double or single) to the end of each day, fitting parameters
        subject_sample = random.sample(range(1, len(subjects)), len(subjects) - 1)
        temp_set = subject_set

        for grade in range(0, grades):
            for day in range(0, len(school_days)):
                temp_periods = 7 - master_subject_array[grade][day][0]
                index = 0
                    #This condition-controlled iteration determines which subjects get double blocks per day.
                for index in range(0, len(subjects) - 1):
                    if temp_periods > 0:
                        if temp_periods > 1:
                            d_or_s = random.randint(1, 2)
                            if d_or_s == 2:
                                temp_periods = temp_periods - 1
                        master_subject_array[grade][day][subject_sample[index]] = d_or_s
                        temp_periods = temp_periods - 1
        
        ranked_subject_arrays.append((subject_fitness(master_subject_array), master_subject_array))
        ranked_subject_arrays.sort()

def timetable_construct():

    global ranked_subject_arrays, block_content

    healthiest = ranked_subject_arrays[0][0]
    best_set = ranked_subject_arrays[0][1]
    collection = ranked_subject_arrays[:100]
    timetable = [9999999, [], [], [], []]

    # Once we have our first healthy batch, we want to mutate it many times
    # We can actually let the user decide how many times to mutate the array

    ranked_subject_arrays = []
    ranked_subject_arrays.append((healthiest, best_set))
    #here, the program randomises a selection of possible subject combinations, and is compared using a fitness subroutine
    for iteration in range(iterations):
        master_subject_array = []

        current_set = random.choice(collection)
        current_set = current_set[1]

        for grade in range(0, len(current_set)):
            master_subject_array.append([])
            for days in range(0, len(current_set[grade])):
                master_subject_array[grade].append([])
                master_subject_array[grade][days].append(current_set[grade][days][0])
                for i in range(1, len(current_set[grade][days])):
                    if current_set[grade][days][i] > 0:
                        choice = random.randint(1, 2)
                        master_subject_array[grade][days].append(choice)
                    else:
                        master_subject_array[grade][days].append(0)
        
        ranked_subject_arrays.append((subject_fitness(master_subject_array), master_subject_array))
        ranked_subject_arrays.sort()

    if ranked_subject_arrays[0][0] < healthiest:
        healthiest = ranked_subject_arrays[0][0]
        best_set = ranked_subject_arrays[0][1]
        collection = ranked_subject_arrays[:100]

    for index in range(iterations // 100):
        
        total_issues = 0
        healthiest_set = []
        temp_array = ranked_subject_arrays[index][1]
        clashes = []
        overlaps = []
        #logs clashes and overlaps
        for i in range(0, len(school_days)):
            clashes.append([])
            overlaps.append([])
            for _ in range(0, periods):
                clashes[i].append(0)
                overlaps[i].append(0)
            
        for day in range(0, len(school_days)):
            healthiest_set.append([])
            lowest_issues = [99999, []]
            temp_db = str(school_days[day])
            
            for iteration in range(iterations // 100):
                
                day_setup(school_days[day], grades, periods)
                g = []
                for grade in range(0, grades):
                    g.append([])
                    subject_set = random.sample(subjects, len(subjects))
                    x = 1 #too many period variable names, using this as a substitute.
                    
                    for j in range(0, len(subjects)):
                        
                        current_subject = temp_array[grade][day][subject_set[j]]
                        
                        while current_subject > 0:
                            g[grade].append(subject_set[j])
                            
                            temp = int(db.execute("select clash_id from clash where block = ?;", (g[grade][-1] - 1))[0]["clash_id"])

                            if len(db.execute("select * from ? where exists(select period from ? where period = ?);", temp_db, temp_db, str(x))) == 0:
                                db.execute("insert into ?('period') values(?);", temp_db, str(x))
                                db.execute("insert into ?('period') values(?);", temp_db + "_error", str(x))
                            db.execute("update ? set ? = ? where period = ?;", temp_db, str("grade_" + str(grade)), str(temp), str(x))
                            x += 1
                            current_subject -= 1

                construct_errors(g, school_days[day], grades, clash_condition)
                temp_issues = construct_fitness(g, periods, school_days[day], grades, clash_condition)
                if temp_issues[0] < lowest_issues[0]:
                    #assigning new values for clashes and overlaps
                    temp_clash = db.execute("select period from ? where clash = 1;", str(school_days[day] + "_error"))
                    temp_overlap = db.execute("select period from ? where overlap = 1;", str(school_days[day] + "_error"))
                    clashes[day] = (error_log(clashes[day], temp_clash, periods))
                    overlaps[day] = (error_log(overlaps[day], temp_overlap, periods))
                    healthiest_set[day] = (g)
                    lowest_issues = temp_issues


            total_issues += lowest_issues[0]
        total_issues += ranked_subject_arrays[index][0]
        if total_issues < timetable[0]:
            timetable[0] = total_issues
            timetable[1] = healthiest_set
            timetable[2] = ranked_subject_arrays[index]
            timetable[3] = clashes
            timetable[4] = overlaps
