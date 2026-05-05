from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    photo_filename = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=0)
    min_threshold = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float)
    location_id = db.Column(db.Integer, db.ForeignKey('bin.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    location = db.relationship('Bin', backref='parts')
    stock_logs = db.relationship('StockLog', backref='part', order_by='StockLog.created_at.desc()')

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_threshold


class Bin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shelf = db.Column(db.String(50))
    row = db.Column(db.String(50))
    position = db.Column(db.String(50))
    accessibility = db.Column(db.Integer, default=5)  # 1=hard to reach, 10=easy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def full_label(self):
        parts = [self.shelf, self.row, self.position]
        return '-'.join(p for p in parts if p)


class StockLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)
    change = db.Column(db.Integer, nullable=False)  # positive=received, negative=used
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
