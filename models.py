from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association table for the many-to-many relationship between Parts and Bins
part_bin = db.Table(
    'part_bin',
    db.Column('part_id', db.Integer, db.ForeignKey('part.id'), primary_key=True),
    db.Column('bin_id', db.Integer, db.ForeignKey('bin.id'), primary_key=True),
)


class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    photo_filename = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=0)
    min_threshold = db.Column(db.Integer, default=0)
    usage_count = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    locations = db.relationship('Bin', secondary=part_bin, backref='parts')

    @property
    def is_low_stock(self):
        return self.min_threshold > 0 and self.quantity <= self.min_threshold


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
