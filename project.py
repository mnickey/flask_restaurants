from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Making an API Endpoint (GET request)
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItem=[item.serialize for item in items])

@app.route('/restaurant/<int:restaurant_id>/menu/<menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=menuItem.serialize)

@app.route('/')
@app.route('/restaurant/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    return render_template('menu.html', restaurant=restaurant, items=items)

@app.route('/restaurant/<int:restaurant_id>/new/', methods=['GET', 'POST'])
#Task 1: Create route for newMenuItem function here
def newMenuItem(restaurant_id):
    if request.method == 'POST':
        newItem = MenuItem(name = request.form['name'],restaurant_id=restaurant_id)
        session.add(newItem)
        session.commit()
        flash("New menu item created")
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))
    else:
        return render_template('newMenuItem.html', restaurant_id = restaurant_id )

@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/', methods=['GET', 'POST'])
#Task 2: Create route for editMenuItem function here
def editMenuItem(restaurant_id, menu_id):
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        editedItem.name = request.form['name']
        editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash("Menu Item Successfully Edited")
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item = editedItem)

@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/', methods=['GET', 'POST'])
#Task 3: Create a route for deleteMenuItem function here
def deleteMenuItem(restaurant_id, menu_id):
    itemToDelete = session.query(MenuItem).filter_by(id = menu_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Menu Item Successfully Deleted")
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))
    else:
        return render_template('deletemenuitem.html',restaurant_id = restaurant_id, item = itemToDelete)

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
