import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database
engine = create_engine("postgres://gjvdtouuvldffh:ca3a92edb19dcb6fb967df6d972b81980491effc8c442671e6c9d39e7d3eeb22@ec2-54-228-251-117.eu-west-1.compute.amazonaws.com:5432/d9qchv36s8msrn")
db = scoped_session(sessionmaker(bind=engine))

# Open csv file in reader and skip header
f = open("books.csv")
reader = csv.reader(f)
next(reader)

# Iterate over file, adding rows to database
for isbn, title, author, year in reader:
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", {"isbn": isbn, "title": title, "author": author, "year": year})

# Commit changes
db.commit()