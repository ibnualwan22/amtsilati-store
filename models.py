# models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    availability = db.Column(db.String(50), default='Tersedia')
    link_ig = db.Column(db.String(255))
    link_wa = db.Column(db.String(255))
    link_shopee = db.Column(db.String(255))
    link_tiktok = db.Column(db.String(255))
    image_filename = db.Column(db.String(255))

class OfflineBuyer(db.Model):
    __tablename__ = 'offline_buyers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.Text)
    dormitory = db.Column(db.String(100))
    sales = db.relationship('OfflineSale', backref='buyer', lazy=True)

class OfflineSale(db.Model):
    __tablename__ = 'offline_sales'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('offline_buyers.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.Enum('Lunas', 'Belum Lunas'), default='Lunas')
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    book = db.relationship('Book')

class OnlineSale(db.Model):
    __tablename__ = 'online_sales'
    id = db.Column(db.Integer, primary_key=True)
    buyer_name = db.Column(db.String(255), nullable=False)
    buyer_address = db.Column(db.Text, nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    shipping_cost = db.Column(db.Numeric(10, 2))
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    transfer_date = db.Column(db.Date)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    book = db.relationship('Book')

class CashRecord(db.Model):
    __tablename__ = 'cash_records'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum('debit', 'kredit'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    record_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)