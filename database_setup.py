
"""
 Beginning config for database
"""
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
Base = declarative_base()

# Creating the tables
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250), nullable=False)

class Restaurant(Base):
    __tablename__ = 'restaurant'
    name = Column( String(80), nullable=False)
    id = Column( Integer, primary_key=True )
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
        }

class MenuItem(Base):
    __tablename__ = 'menu_item'
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    course = Column(String(250))
    description = Column(String(250))
    price = Column(String(8))
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
    restaurant = relationship(Restaurant)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    # adding JSON in a serializable object
    @property
    def serialize(self):
        return {
            'name' : self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
            'course': self.course,
        }
# Ending of config for database
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.create_all(engine)

from sqlalchemy.orm import sessionmaker
DBSession = sessionmaker(bind=engine)
session = DBSession()
