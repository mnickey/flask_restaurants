from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, make_response
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User

# New Imports
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
# Todo Add authentication with flask-login

engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
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

    #Use token to get user info from API
    userinfo_url =  "https://graph.facebook.com/v2.2/me"

    #strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.2/me?%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

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

    facebook_id = login_session['facebook_id']
    # print "LOGIN SESSION: {}".format(login_session)

    if facebook_id is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    # headers = h.request(url, 'GET')[1]

    headers = h.request(url, 'DELETE')
    # headers = json.loads(headers)
    print "HEADERS: {}".format(headers)

    # headers = json.loads(h.request(url, 'GET')[1])

    if headers['status'] == '200':
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['facebook_id']

        response = make_response(json.dumps('User successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash("You have been logged out.")
        return response

    else:
        response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        flash("You could not be logged out. Result Status: %s" % (headers['status']) )
        return response

@app.route('/gconnect', methods=['POST'])
def gconnect():
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
        # Reset the user's session
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('User successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return  response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response

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
    :return: shows all the menu items of a given restaurant by restaurant id.
    """
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItem=[item.serialize for item in items])

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/', methods=['GET'])
def menuItemJSON(restaurant_id, menu_id):
    """
    :param restaurant_id:
    :param menu_id:
    :return: a specific menu item from a specific restaurant.
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
    return render_template('final_main.html', restaurants=restaurants)

# @app.errorhandler(404)
@app.route('/restaurants/<int:restaurant_id>/')
@app.route('/restaurants/<int:restaurant_id>/menu/')
def showRestaurant(restaurant_id):
    """
    :param restaurant_id:
    :return: shows the main page of a single restaurant
    """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    # No creator needed since no changes are being made with this route.
    return render_template('final_showrestaurant.html', restaurant = restaurant, items = items )

@app.errorhandler(404)
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

@app.errorhandler(404)
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
        return render_template('final_showrestaurantmenu.html', restaurant = restaurant)

    if request.method == 'POST':
        restaurant = Restaurant(request.form['name'], user_id = login_session['user_id'])
        session.add(restaurant)
        session.commit()
        flash("Restaurant successfully edited")
        return redirect('/')
    else:
        return render_template('final_editrestaurant.html', restaurant=restaurant)

@app.errorhandler(404)
@app.route('/restaurants/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    """
    :param restaurant_id:
    :return: allows the user to delete a restaurant
    """
    # TODO Find a place to create a link for this route that makes sense
    if 'username' not in login_session:
        return redirect('/login')

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        flash('Only the creator of the restaurant can delete a restaurant.')
        return render_template('final_showrestaurantmenu.html', restaurant = restaurant)

    if request.method == 'POST':
        session.delete(restaurant)
        session.commit()
        flash("Restaurant successfully deleted")
        return redirect("/")
    else:
        return render_template('final_deleterestaurant.html', restaurant = restaurant )

@app.errorhandler(404)
@app.route('/restaurants/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    """
    :param restaurant_id:
    :return: Allows the user to create a new menu item for the restaurant with the ID specified
    """
    if 'username' not in login_session:
        return redirect('/login')

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    if 'username' not in login_session or creator.id != restaurant.user_id:
        flash('Only the creator of the restaurant can create a new menu item.')
        return render_template('final_showrestaurantmenu.html', restaurant = restaurant)

    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'])
        newItem.price = request.form['price']
        newItem.description = request.form['description']
        newItem.course = request.form['course']
        newItem.restaurant_id = restaurant_id
        newItem.user = login_session['user_id']
        session.add(newItem)
        session.commit()
        flash("New Menu Item Created")
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

    if 'username' not in login_session or creator.id != restaurant.user_id:
        flash('Only the creator of the restaurant can edit a menu item.')
        return render_template('final_showrestaurantmenu.html', restaurant = restaurant)

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

    if 'username' not in login_session or creator.id != restaurant.user_id:
        flash('Only the creator of the restaurant can delete a menu item.')
        return render_template('final_showrestaurantmenu.html', restaurant = restaurant)

    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash("Item successfully deleted")
        return redirect(url_for('showRestaurant', restaurant_id = restaurant_id))
    else:
        return render_template('final_deletemenuitem.html', item = deletedItem, restaurant = restaurant)

def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None

def getUserInfo(user_id):
    user = session.query(User).filter_by(id = user_id).one()
    return user

def createUser(login_session):
    newUser = User(name = login_session['username'], email = login_session['email'],
                   picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
