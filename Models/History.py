from Models.Model import Database
from Models.Model import Model


class History(Model):
    __tablename__ = 'histories'
    id = Database.Column(Database.Integer, primary_key=True, nullable=False, autoincrement=True)
    last_match_id = Database.Column(Database.Integer, nullable=False)
