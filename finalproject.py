from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, make_response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import random, string
import httplib2
import json
import requests
import smtplib

app = Flask(__name__)

# Load client keys
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Create database engine
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

#Create anti-forgery state token
@app.route('/login')
def showLogin():
    """
    Creating a route to let the user login with G+ or Facebook
    :return: A HTML page that has options for the user to login with
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """
    Creating a route to let the user connect with Facebook
    :return: Once connected the user will see a message that they have been connected
    The user will then be returned to the main page.
    """
    if request.args.get('state') !=login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # set the access token
    access_token = request.data

    # Exchange short lived token for long lived token
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id,app_secret,access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    #strip expire tag from access token
    token = result.split("&")[0]
    the_access_token = token.split("=")[1]

    url = 'https://graph.facebook.com/v2.2/me?%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    login_session['access_token'] = the_access_token

    #Get user picture
    url = 'https://graph.facebook.com/v2.2/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # set the output info
    output = ''
    output +='<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash ("Now logged in as %s" % login_session['username'])
    return output

@app.route('/fbdisconnect', methods=['GET', 'POST', 'DELETE'])
def fbdisconnect():

    facebook_id = login_session.get('facebook_id')
    access_token = login_session.get('access_token')

    if facebook_id is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        flash("User not connected.")
        return redirect('/restaurants')

    else:
        url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
        h = httplib2.Http()
        result = h.request(url, 'DELETE')[1]
        # Resetting the user login with FB is now being done in the disconnect function.
        # Items reset in the disconnect function are: ['username'], ['email'], ['picture'],
        # ['user_id'] and ['facebook_id']

        response = make_response(json.dumps('User successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash("Your FB login session has been removed and you have been logged out.")
        return redirect('/restaurants')

@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Connects the user with Google+ account
    :return: Once connected this will return a flash message letting the user know they have connected
    and redirect them to the main page.
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    code = request.data
    try:
        # Upgrade the auth code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
        json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    #Get user info
    userinfo_url =  "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # Check to see if the user exists, if they do - continue, If they do not, create a user
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output +='<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s"%login_session['username'])
    print "done!"
    return output

# Disconnect user - Revoke a users token and reset the session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Execute HTTP GET request to revoke current token
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's session -- now being done in the disconnect function
        # Items removed in the disconnect function are: ['credentials'], ['gplus_id'], ['username']
        # ['email'] and ['picture']
        response = make_response(json.dumps('User successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return  response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response

# ***** JSON Routes *****
@app.route('/restaurants/JSON/', methods=['GET'])
def restaurant_JSON():
    """
    :param restaurant_id:
    :return: JSON representation of restaurants available.
    """
    restaurants = session.query(Restaurant)
    return jsonify(Restaurant=[restaurant.serialize for restaurant in restaurants])

@app.route('/restaurants/<int:restaurant_id>/menu/JSON/', methods=['GET'])
def restaurant_menu(restaurant_id):
    """
    :param restaurant_id:
    :return: shows all the menu items of a given restaurant by restaurant id in JSON format
    """
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItem=[item.serialize for item in items])

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/', methods=['GET'])
def menuItemJSON(restaurant_id, menu_id):
    """
    :param restaurant_id:
    :param menu_id:
    :return: a JSON representation of a specific menu item from a specific restaurant.
    """
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=menuItem.serialize)

@app.route('/')
@app.route('/restaurants/')
def index():
    """
    :return: all the restaurants that are in the database
    :param -- none
    """
    restaurants = session.query(Restaurant).all()
    if 'user_id' not in login_session:
        user = '' # Trying to enable guest mode
    else:
        user = getUserInfo(login_session['user_id'])
    return render_template('final_main.html', restaurants=restaurants, User=user)

@app.route('/restaurants/<int:restaurant_id>/')
@app.route('/restaurants/<int:restaurant_id>/menu/')
def showRestaurant(restaurant_id):
    """
    :param restaurant_id:
    :return: shows the main page of a single restaurant
    """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    creator = getUserInfo(restaurant.user_id)
    if 'user_id' not in login_session:
        user = '' # Trying to enable guest mode
    else:
        user = getUserInfo(login_session['user_id'])
    return render_template('final_showrestaurant.html', restaurant=restaurant, items=items, CREATOR=creator, User=user)

@app.route('/restaurants/new/', methods=['GET', 'POST'])
def newRestaurant():
    """
    :return: a form that allows the user to create a new restaurant
    """
    if 'username' not in login_session:
        flash('You must be logged in to create a restaurant.')
        return redirect('/login')
    if request.method == 'POST':
        newRestaurant = Restaurant(name = request.form['name'], user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        flash("New Restaurant Created")
        return redirect('/')
    else:
        return render_template('final_newrestaurant.html')

@app.route('/restaurants/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    """
    :param restaurant_id:
    :return: allows the user to EDIT a restaurants name
    """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)

    if 'username' not in login_session:
        return redirect('/login')

    if 'username' not in login_session or creator.id != login_session['user_id']:
        flash('Only the creator of the restaurant can edit the restaurant name.')
        return render_template('final_showrestaurant.html', restaurant = restaurant)

    if request.method == 'POST':
        restaurant = Restaurant(request.form['name'], user_id = login_session['user_id'])
        session.add(restaurant)
        session.commit()
        flash("Restaurant successfully edited")
        return redirect('/')
    else:
        return render_template('final_editrestaurant.html', restaurant=restaurant)

@app.route('/restaurants/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    """
    :param restaurant_id:
    :return: allows the user to delete a restaurant
    """
    if 'username' not in login_session:
        return redirect('/login')

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        flash('Only the creator of the restaurant can delete a restaurant.')
        return render_template('final_showrestaurant.html', restaurant = restaurant)

    if request.method == 'POST':
        session.delete(restaurant)
        session.commit()
        flash("Restaurant successfully deleted")
        return redirect("/")
    else:
        return render_template('final_deleterestaurant.html', restaurant = restaurant )

@app.route('/restaurants/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    """
    :param restaurant_id:
    :return: Allows the user to create a new menu item for the restaurant with the ID specified
    """
    if 'username' not in login_session:
        return redirect('/login')

    # Get the restaurant, items and creator
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    creator = getUserInfo(restaurant.user_id)

    # checks to see if the user is logged in or not
    if 'username' not in login_session or creator.id != login_session['user_id']:
        flash('Only the creator of the restaurant can create a new menu item.')
        return render_template('final_showrestaurant.html', restaurant=restaurant, items=items, CREATOR=creator)

    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'])
        newItem.price = request.form['price']
        newItem.description = request.form['description']
        newItem.course = request.form['course']
        newItem.restaurant_id = restaurant_id
        # newItem.user = login_session['user_id']
        session.add(newItem)
        session.commit()
        flash("New Menu Item Created", "success")
        return redirect( url_for('showRestaurant', restaurant_id = restaurant_id) )
    else:
        return render_template('final_newmenuitem.html', restaurant_id=restaurant_id)

@app.errorhandler(404)
def page_not_found(e):
    """
    :param e for error code 404 Not Found:
    :return: returns a 404 error page telling the user that there is nothing at the link they visited
    Also has a return link to the main page.
    """
    return render_template('404.html'), 404

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    """
    :param restaurant_id:
    :param menu_id:
    :return: Allows the user to edit a menu item
    """
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    editedItem = session.query(MenuItem).filter_by(id = menu_id).one()
    creator = getUserInfo(restaurant.user_id)
    user = getUserInfo(login_session['user_id'])

    if 'username' not in login_session or creator.id != login_session['user_id']:
        flash('Only the creator of the restaurant can edit a menu item.')
        return render_template('final_showrestaurant.html', restaurant=restaurant, User=user, CREATOR=creator)

    if request.method == 'POST':
        editedItem.name = request.form['name']
        editedItem.price = request.form['price']
        editedItem.description = request.form['description']
        editedItem.course = request.form['course']
        editedItem.user = login_session['user_id']
        session.add(editedItem)
        session.commit()
        flash("Item successfully edited")
        return redirect( url_for('showRestaurant', restaurant_id = restaurant_id ) )
    else:
        return render_template('final_editmenuitem.html', editedItem=editedItem, restaurant=restaurant )

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/delete', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    """
    :param restaurant_id:
    :param menu_id:
    :return: allows a user to delete a menu item from a restaurant
    """
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    deletedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    creator = getUserInfo(restaurant.user_id)
    user = getUserInfo(login_session['user_id'])

    if 'username' not in login_session or creator.id != login_session['user_id']:
        flash('Only the creator of the restaurant can delete a menu item.')
        return render_template('final_showrestaurant.html', restaurant=restaurant, User=user, CREATOR=creator)

    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash("Item successfully deleted")
        return redirect(url_for('showRestaurant', restaurant_id = restaurant_id))
    else:
        return render_template('final_deletemenuitem.html', item = deletedItem, restaurant = restaurant)

def getUserID(email):
    """
    :param email:
    :return: The user.id is returned based on the email address given
    """
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None

def getUserInfo(user_id):
    """
    Helper function to get the user information based on user_id
    :param user_id:
    """
    user = session.query(User).filter_by(id = user_id).one()
    return user

def createUser(login_session):
    """
    Gives the ability to create a new user.
    :param login_session:
    """
    newUser = User(name = login_session['username'], email = login_session['email'],
                   picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id

@app.route('/contact/', methods=['GET', 'POST'])
def contactUs():
    """
    Give the user a way to communicate with the creator of this site...ME!
    P.S. This actually works so feel free to send an email if you're bored.
    :return: A contact form to send mail to the creator ... ME!
    """
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login('mnickey@gmail.com', 'qubjqsxsscqikwdj')
    if request.method == 'POST':
        fromAddress = request.form['email_address']
        contactMessage = request.form['message']
        mail.sendmail(fromAddress, 'mnickey@gmail.com', contactMessage + " " + fromAddress)
        mail.close()
        flash("Your message was successfully sent. Someone will get back to you as soon as possible.")
        return redirect(url_for('index'))
    else:
        return render_template('finalContact.html')

@app.route('/disconnect')
def disconnect():
    """
    Give the ability to disconect a user after they have connected.
    This will make use of the helper functions for both FB and G+, removing the proprietary login session information
     then this will remove the login_session information that is common between the two.
    :return:
    """
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have been successfully disconnected.")
        return redirect(url_for('index'))
    else:
        flash("You were not logged in.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
