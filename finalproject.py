from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from pprint import pprint as pp

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def index():
    """
    :return: all the restaurants that are in the database
    :param -- none
    """
    restaurants = session.query(Restaurant).all()
    return render_template('final_main.html', restaurants=restaurants)

@app.route('/restaurants/<int:restaurant_id>/')
@app.route('/restaurants/<int:restaurant_id>/menu/')
# THIS IS A DUPLICATE ROUTE. @app.route combined in the showRestaurant function
def showRestaurant(restaurant_id):
    """
    :param restaurant_id:
    :return: shows the main page of a single restaurant
    """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    return render_template('final_showrestaurant.html', restaurant = restaurant, items = items )

@app.route('/restaurants/new/', methods=['GET', 'POST'])
def newRestaurant():
    """
    :return: a form that allows the user to create a new restaurant
    """
    if request.method == 'POST':
        newRestaurant = Restaurant(name = request.form['name'])
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
    if request.method == 'POST':
        restaurant.name = request.form['name']
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
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
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
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'])
        newItem.price = request.form['price']
        newItem.description = request.form['description']
        newItem.course = request.form['course']
        newItem.restaurant_id = restaurant_id
        session.add(newItem)
        session.commit()
        flash("New Menu Item Created")
        return redirect( url_for('showRestaurant', restaurant_id = restaurant_id) )
    else:
        return render_template('final_newmenuitem.html', restaurant_id=restaurant_id)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    """
    :param restaurant_id:
    :param menu_id:
    :return: Allows the user to edit a menu item
    """
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    editedItem = session.query(MenuItem).filter_by(id = menu_id).one()
    # editedItem = session.query(MenuItem).filter_by(restaurant_id=restaurant.id, id=menu_id).one()
    # editedItem = session.query(MenuItem).get(menu_id)
    # editedItem = session.query(MenuItem).filter(restaurant.id == restaurant_id, MenuItem.id==menu_id).one()
    if request.method == 'POST':
        editedItem.name = request.form['name']
        editedItem.price = request.form['price']
        editedItem.description = request.form['description']
        editedItem.course = request.form['course']
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
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    deletedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash("Menu Item successfully deleted")
        return redirect(url_for('showRestaurant', restaurant_id = restaurant_id))
    else:
        return render_template('final_deletemenuitem.html', item = deletedItem, restaurant = restaurant)

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
