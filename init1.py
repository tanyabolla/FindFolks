#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors

#Initialize the app from Flask
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='password',
                       db='meetup3',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

def authLoggedIn():
	try:
		print session['username']
	except KeyError:
		return False
	return True

#Define a route to hello function
@app.route('/')
def index():
	print session
	#make connection
	cursor = conn.cursor()
	#write up query string
	query = 'SELECT * from interest'
	#execute query string with prams (no params this time)
	cursor.execute(query, ())
	#retrive results
	interests = cursor.fetchall()


	query = 'SELECT * FROM an_event WHERE start_time <= DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 3 DAY)'
	cursor.execute(query, ())
	upcomingEvents = cursor.fetchall()
	#close connection
	cursor.close()

	return render_template('index.html', interests = interests, upcomingEvents = upcomingEvents)

#define func for groups of interest x
@app.route('/groupsOfInterest', methods = ['GET', 'POST'])
def groupsOfInterest():
	interest = request.form['interest']
	interest = interest.split(', ')
	keyword = interest[0]
	category = interest[1]
	print category, keyword
	cursor = conn.cursor()
	#query = 'SELECT * FROM about'
	query = 'SELECT * FROM about NATURAL JOIN a_group WHERE category = %s AND keyword = %s'
	cursor.execute(query, (category, keyword))
	groups = cursor.fetchall()
	cursor.close()
	return render_template('groupsOfInterest.html', groups = groups)

#display groups that user may join
@app.route('/groups')
def groups():
	cursor = conn.cursor()
	query = 'SELECT * FROM a_group'
	cursor.execute(query, ())
	groups = cursor.fetchall()
	return render_template('groups.html', groups = groups)

#Define route for login
@app.route('/login')
def login():
	return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
	return render_template('register.html')


#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password']

	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM member WHERE username = %s AND password = md5(%s)'
	cursor.execute(query, (username, password))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	cursor.close()
	error = None
	if(data):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		print session['username']
		return redirect(url_for('home'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password']
	firstname = request.form['firstname']
	lastname = request.form['lastname']
	email = request.form['email']
	zipcode = request.form['zipcode']

	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM member WHERE username = %s'
	cursor.execute(query, (username))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	error = None
	if(data):
		#If the previous query returns data, then user exists
		error = "This user already exists"
		return render_template('register.html', error = error)
	else:
		ins = 'INSERT INTO member(username, password, firstname, lastname, email, zipcode) VALUES(%s, md5(%s), %s, %s, %s, %s)'
		cursor.execute(ins, (username, password, firstname, lastname, email, zipcode))
		conn.commit()
		cursor.close()
		return render_template('index.html')

@app.route('/home')
def home():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	username = session['username']
	cursor = conn.cursor();
	query = 'SELECT * FROM member NATURAL JOIN belongs_to NATURAL JOIN a_group WHERE username = %s'
	cursor.execute(query, (username))
	groups = cursor.fetchall()
	cursor.close()
	return render_template('home.html', username=username, groups=groups)


@app.route('/logout')
def logout():
	session.pop('username')
	print session
	return redirect('/')

#tanya, case 3
@app.route('/upcomingEvents')
def upcomingEvents():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	username = session['username']
	cursor = conn.cursor()
	query = 'SELECT * FROM an_event WHERE start_time <= DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 3 DAY) AND event_id IN (SELECT event_id FROM sign_up WHERE username = %s)'
	cursor.execute(query, (username))
	events = cursor.fetchall()

	query = 'SELECT * FROM member NATURAL JOIN belongs_to NATURAL JOIN a_group WHERE username = %s'
	cursor.execute(query, (username))
	groups = cursor.fetchall()
	cursor.close()
	return render_template('upcomingEvents.html', username=username, events=events, groups=groups)

#tanya, case 3, search events by group
@app.route('/eventsOfGroups', methods=['GET', 'POST'])
def eventsOfGroup():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	groupName = request.form['groups']
	print groupName
	username = session['username']
	cursor = conn.cursor()
	query = 'SELECT * FROM an_event WHERE event_id IN (SELECT event_id FROM organize WHERE group_id IN (SELECT group_id FROM a_group WHERE group_name = %s))'
	cursor.execute(query, (groupName))
	events = cursor.fetchall()
	cursor.close();
	return render_template('eventsOfGroups.html', username=username, events=events)

#dayan, case 4 and 5, shows past event to be rated, future events, and events of interest
#assuming user can not sign up for events they do not have an interest in
@app.route('/searchEventsOfInterest')
def searchEventsOfInterest():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	
	username = session['username']

	cursor = conn.cursor()
	#gives us all the events that are organized by groups the user shares an interest with
	query = 'SELECT * FROM about NATURAL JOIN organize NATURAL JOIN an_event WHERE (start_time > CURRENT_TIMESTAMP) AND (category, keyword) IN (SELECT category, keyword FROM interested_in WHERE username = %s) AND event_id NOT IN (SELECT event_id FROM sign_up WHERE username = %s)'
	cursor.execute(query, (username, username))
	interestingEvents = cursor.fetchall() #does not have events user already signed up for
	query = 'SELECT * FROM sign_up NATURAL JOIN an_event NATURAL JOIN organize WHERE username = %s AND (start_time > CURRENT_TIMESTAMP)'
	cursor.execute(query, (username))
	userEvents = cursor.fetchall() #has future events user already signed up for
	query = 'SELECT * FROM sign_up NATURAL JOIN an_event NATURAL JOIN organize WHERE username = %s AND (start_time < CURRENT_TIMESTAMP)'
	cursor.execute(query, (username))
	pastUserEvents = cursor.fetchall()
	cursor.close()
	return render_template('searchEventsOfInterest.html', interestingEvents = interestingEvents, userEvents = userEvents, pastUserEvents = pastUserEvents)

#dayan,case 4 user gets a list of events to choose from and they sign up for one, can only show events they have interest in
@app.route('/signUpForEvent')
def signUpForEvent():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	username = session['username']
	cursor = conn.cursor()
	query = 'SELECT * FROM about NATURAL JOIN organize NATURAL JOIN an_event WHERE (start_time > CURRENT_TIMESTAMP) AND (category, keyword) IN (SELECT category, keyword FROM interested_in WHERE username = %s) AND event_id NOT IN (SELECT event_id FROM sign_up WHERE username = %s)'
	cursor.execute(query, (username, username))
	interestingEvents = cursor.fetchall() #does not have events user already signed up for
	cursor.close()
	return render_template('signUpForEvent.html', interestingEvents = interestingEvents)

#dayan, case 4 exec, we get an event from /signUpForEvent and we insert in sign_up table
@app.route('/signUserUpForEvent', methods=['GET', 'POST'])
def signUserUpForEvent(): #coming from /signUpForEvent
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	username = session['username']
	event = request.form['event']
	event = event.split(':')
	eventID = event[0]
	cursor = conn.cursor()
	insQ = 'INSERT INTO sign_up (event_id, username, rating) VALUES (%s, %s, %s)'
	cursor.execute(insQ, (eventID, username, 0))
	conn.commit()

	return redirect('/home')



@app.route('/viewAveRating')
def viewAveRating():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')

	username = session['username']
	cursor = conn.cursor()
	#query returns event_id, name and average rating for all previous events from users groups
	query = 'SELECT event_id, title, AVG(rating) as average_rating FROM organize NATURAL JOIN sign_up NATURAL JOIN an_event WHERE group_id IN (SELECT group_id FROM belongs_to WHERE username = %s) AND (start_time < CURRENT_TIMESTAMP AND start_time >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 3 DAY) ) GROUP BY event_id'
	cursor.execute(query, (username))
	eventRating = cursor.fetchall()
	cursor.close()
	return render_template('viewAveRating.html', eventRating = eventRating)


@app.route('/unfriend')
def unfriend():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')

	username = session['username']
	cursor = conn.cursor()
	#query returns all this persons friends
	query = 'SELECT * FROM friend WHERE friend_of = %s'
	cursor.execute(query, (username))
	friends = cursor.fetchall()
	cursor.close()
	return render_template('unfriend.html', friends = friends)



#Tanya, #6, shows the groups user is authorized to make events for
@app.route('/createEvent')
def createEvent():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	username = session['username']
	cursor = conn.cursor()
	#query returns the groups which the user can create events for
	query = 'SELECT * FROM belongs_to NATURAL JOIN a_group WHERE username = %s AND authorized = 1'
	cursor.execute(query, (username))
	groups = cursor.fetchall()
	cursor.close()
	#createEvent.html allows user to choose which group to add an event for
	return render_template('createEvent.html', username=username, groups=groups)

#Tanya, #6, makes user fill in info for making an event
@app.route('/eventCreationForm', methods=['GET', 'POST'])
def eventCreationForm():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	#creates a session for the group
	groupID = request.form['groupToCreate']
	groupID = groupID.split(':')
	session['group_id'] = groupID[0]
	cursor = conn.cursor()
	query = 'SELECT * FROM location'
	cursor.execute(query, ())
	locations = cursor.fetchall()
	cursor.close();
	#eventCreationForm.html shows a form for the user to fill to create an event
	#Submitting the form redirects it to /insertEvent which inserts the event into the database
	return render_template('eventCreationForm.html', locations=locations)

#Tanya, #6, creates event using users info, inserts to database
@app.route('/insertEvent', methods=['GET', 'POST'])
def insertEvent():
	if not authLoggedIn():
		return render_template('notLoggedIn.html')
	username = session['username']
	groupID = session['group_id']
	cursor = conn.cursor()
	#gets information from the submitted form in /eventCreationForm
	title = request.form['title']
	description = request.form['description']
	startTime = request.form['startTime']
	endTime = request.form['endTime']
	place = request.form['location']
	place = place.split(',')
	location = place[0]
	zipcode = place[1]
	#inputs the event into the database
	query1 = 'INSERT INTO an_event (title, description, start_time, end_time, location_name, zipcode) VALUES (%s, %s, %s, %s, %s, %s)'
	cursor.execute(query1, (title, description, startTime, endTime, location, zipcode))
	#event_id has a auto-increment feature, where it automatically gives the event a specific id
	#cursor is in the an_event section table of the database
	#lastrowid attribute allows us to get the last event_id and since the event we added
	#is the last event, it is the event_id of the new event
	event_id = cursor.lastrowid
	query2 = 'INSERT INTO organize(event_id, group_id) VALUES (%s, %s)'
	cursor.execute(query2, (event_id, groupID))
	query3 = 'INSERT INTO sign_up(event_id, username, rating) VALUES (%s, %s, 0)'
	cursor.execute(query3, (event_id, username)) #assuming creator of event automatically goes to event 
	#updates the database
	conn.commit()
	cursor.close()
	#returns to the createEvent page
	return redirect(url_for('home'))



#Tanya additional feature create Friends
@app.route('/makeFriends', methods=['GET', 'POST'])
def makeFriends():
	username = session['username']
	cursor = conn.cursor()
	query = 'SELECT * FROM friend WHERE friend_of = %s'
	cursor.execute(query, (username))
	friends = cursor.fetchall()
	query = 'SELECT username FROM member WHERE username NOT IN (SELECT friend_to FROM friend WHERE friend_of= %s) AND username != %s'
	cursor.execute(query, (username, username))
	notFriends = cursor.fetchall()
	cursor.close()
	return render_template('makeFriends.html', username=username, friends=friends, notFriends=notFriends)

#Tanya additional feature, insert friends into the database
@app.route('/insertFriends', methods=['GET', 'POST'])
def insertFriends():
	username = session['username']
	friend_name = request.form['friend']
	cursor = conn.cursor()
	query = 'INSERT INTO friend (friend_of, friend_to) VALUES (%s, %s)'
	cursor.execute(query, (username, friend_name))
	conn.commit()
	return redirect(url_for('home'))

# tanya, case 9, view your friends events
@app.route('/friendsEvent')
def friendsEvent():
	username = session['username']
	cursor = conn.cursor()
	query = 'SELECT * FROM an_event NATURAL JOIN sign_up WHERE username IN (SELECT friend_to FROM friend WHERE friend_of = %s)'
	cursor.execute(query, (username))
	friendsEvents = cursor.fetchall()
	return render_template('friendsEvent.html', friendsEvents=friendsEvents)


		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
