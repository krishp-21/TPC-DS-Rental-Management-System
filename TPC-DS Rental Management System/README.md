# TPC-DS Rental Management System

A database systems project for CIS 4301 – Information and Database Systems 1 at the University of Florida (Spring 2026) that implements the query layer for a command-line item rental system through MariaDB.

**Author:** Krish Patel

## Goal

A single Python module that can handle every database operation a rental system needs using parameterized SQL queries.

## Data

The TPC-DS benchmark dataset is an industry-standard dataset that simulates a large retail business. A subset of five TPC-DS tables was used alongside three custom operational tables built for this project.

| Table | Role |
|---|---|
| item | Products available to rent (18,000 rows) |
| customer | Registered customers (100,000 rows) |
| customer_address | Customer mailing addresses (50,000 rows) |
| store_sales | Source for pre-existing rental history |
| date_dim | Converts surrogate date keys to real dates |
| rental | Active rentals |
| rental_history | Completed rentals (2.6M+ rows from store_sales) |
| waitlist | Customers waiting for out-of-stock items |

## What I Did

- Implemented all 20+ functions in db_handler.py which handles every read and write operation between the app and the database (This is the only file I wrote)
- Wrote parameterized SQL queries across 8 relational tables for inventory tracking, rental processing, return handling, and waitlist management
- Built dynamic filtering functions that support any combination of attributes, pattern matching, and inclusive date and price range filters
- Handled TPC-DS-specific data challenges including CHAR column padding, surrogate vs. business key separation, and multi-table inserts with foreign key ordering

## My Contribution

The database schema, data loading script, CLI menus, and data models were provided as part of the assignment. My contribution was db_handler.py.

## Results

- All 20+ functions implemented and passing public test suite
- Filtering functions support exact match and LIKE pattern matching across all string fields
- System handles 2.6M+ row rental history dataset with no performance issues on standard queries

## How to Run

### Prerequisites
- Python 3.10+
- MariaDB 10.6+
- TPC-DS CSV files in a tpcds_data/ folder

### 1. Install dependencies
pip install mariadb


### 2. Enable local file loading in MariaDB
SET GLOBAL local_infile = 1;


### 3. Configure credentials
Create MARIADB_CREDS.py in the project root:

DB_CONFIG = {
    "username": "your_username",
    "password": "your_password",
    "port": 3306,
    "host": "localhost",
    "database": "tpcds_rental",
}


### 4. Load the database

python setup_db.py ./tpcds_data/

### 5. Run the app

python main.py


## Files

- db_handler.py: all database queries and logic (my implementation)
- main.py: entry point and main menu (provided)
- helper_functions.py: business logic and CLI menus (provided)
- setup_db.py: database setup and CSV loader (provided)
- models/: data model classes for Item, Customer, Rental, RentalHistory, Waitlist (provided)
- screenshots/: terminal screenshots of the system running

## Data Source

TPC-DS Benchmark — (https://www.tpc.org/tpcds/)
