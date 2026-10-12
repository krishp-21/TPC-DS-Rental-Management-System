from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.RentalHistory import RentalHistory
from models.Waitlist import Waitlist
from models.Item import Item
from models.Rental import Rental
from models.Customer import Customer
from datetime import date, timedelta


conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])


cur = conn.cursor()


def add_item(new_item: Item = None):
    """
    new_item - an item object containing a new item to be inserted into the database in the item table
    """
    cur.execute(
        "INSERT INTO item (i_item_sk, i_item_id, i_rec_start_date, i_product_name, "
        "i_brand, i_class, i_category, i_manufact, i_current_price, i_num_owned) "
        "VALUES ((SELECT COALESCE(MAX(i_item_sk), 0) + 1 FROM item AS tmp), "
        "?, ?, ?, ?, NULL, ?, ?, ?, ?)",
        (
            new_item.item_id,
            f"{new_item.start_year}-01-01",
            new_item.product_name,
            new_item.brand,
            new_item.category,
            new_item.manufact,
            new_item.current_price,
            new_item.num_owned,
        )
    )


def add_customer(new_customer: Customer = None):
    """
    customer object containing a new customer to be inserted into the database in the customer table
    """
    address_parts = new_customer.address.split(",")
    street_parts = address_parts[0].strip().split(" ", 1)
    street_number = street_parts[0].strip() if len(street_parts) > 0 else ""
    street_name = street_parts[1].strip() if len(street_parts) > 1 else ""
    city = address_parts[1].strip() if len(address_parts) > 1 else ""
    state_zip = address_parts[2].strip() if len(address_parts) > 2 else ""
    state_zip_parts = state_zip.split(" ", 1)
    state = state_zip_parts[0].strip() if len(state_zip_parts) > 0 else ""
    zip_code = state_zip_parts[1].strip() if len(state_zip_parts) > 1 else ""

    cur.execute(
        "INSERT INTO customer_address "
        "(ca_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip) "
        "VALUES ((SELECT COALESCE(MAX(ca_address_sk), 0) + 1 FROM customer_address AS tmp), "
        "?, ?, ?, ?, ?)",
        (street_number, street_name, city, state, zip_code)
    )

    cur.execute("SELECT MAX(ca_address_sk) FROM customer_address")
    addr_sk = cur.fetchone()[0]

    name_parts = new_customer.name.split(" ", 1)
    first_name = name_parts[0].strip() if len(name_parts) > 0 else ""
    last_name = name_parts[1].strip() if len(name_parts) > 1 else ""

    cur.execute(
        "INSERT INTO customer "
        "(c_customer_sk, c_customer_id, c_first_name, c_last_name, c_email_address, c_current_addr_sk) "
        "VALUES ((SELECT COALESCE(MAX(c_customer_sk), 0) + 1 FROM customer AS tmp), "
        "?, ?, ?, ?, ?)",
        (new_customer.customer_id, first_name, last_name, new_customer.email, addr_sk)
    )


def edit_customer(original_customer_id: str = None, new_customer: Customer = None):
    """
    original_customer_id - a string containing the customer id for the customer to be edited
    new_customer - customer object containing attributes to update
    """
    customer_fields = []
    customer_values = []

    if new_customer.customer_id is not None:
        customer_fields.append("c_customer_id = ?")
        customer_values.append(new_customer.customer_id)

    if new_customer.name is not None:
        name_parts = new_customer.name.split(" ", 1)
        first_name = name_parts[0].strip()
        last_name = name_parts[1].strip() if len(name_parts) > 1 else ""
        customer_fields.append("c_first_name = ?")
        customer_values.append(first_name)
        customer_fields.append("c_last_name = ?")
        customer_values.append(last_name)

    if new_customer.email is not None:
        customer_fields.append("c_email_address = ?")
        customer_values.append(new_customer.email)

    if customer_fields:
        customer_values.append(original_customer_id)
        cur.execute(
            f"UPDATE customer SET {', '.join(customer_fields)} WHERE c_customer_id = ?",
            tuple(customer_values)
        )

    if new_customer.address is not None:
        effective_id = new_customer.customer_id if new_customer.customer_id is not None else original_customer_id

        address_parts = new_customer.address.split(",")
        street_parts = address_parts[0].strip().split(" ", 1)
        street_number = street_parts[0].strip() if len(street_parts) > 0 else ""
        street_name = street_parts[1].strip() if len(street_parts) > 1 else ""
        city = address_parts[1].strip() if len(address_parts) > 1 else ""
        state_zip = address_parts[2].strip() if len(address_parts) > 2 else ""
        state_zip_parts = state_zip.split(" ", 1)
        state = state_zip_parts[0].strip() if len(state_zip_parts) > 0 else ""
        zip_code = state_zip_parts[1].strip() if len(state_zip_parts) > 1 else ""

        cur.execute(
            "UPDATE customer_address "
            "SET ca_street_number = ?, ca_street_name = ?, ca_city = ?, ca_state = ?, ca_zip = ? "
            "WHERE ca_address_sk = ("
            "  SELECT c_current_addr_sk FROM customer WHERE c_customer_id = ?"
            ")",
            (street_number, street_name, city, state, zip_code, effective_id)
        )


def rent_item(item_id: str = None, customer_id: str = None):
    """
    item_id - string containing the item id for the item being rented
    customer_id - string containing the customer id of the customer renting the item
    """
    today = date.today()
    due_date = today + timedelta(days=14)
    cur.execute(
        "INSERT INTO rental (item_id, customer_id, rental_date, due_date) VALUES (?, ?, ?, ?)",
        (item_id, customer_id, str(today), str(due_date))
    )


def waitlist_customer(item_id: str = None, customer_id: str = None) -> int:
    """
    returns the customer's new place in line
    """
    new_place = line_length(item_id) + 1
    cur.execute(
        "INSERT INTO waitlist (item_id, customer_id, place_in_line) VALUES (?, ?, ?)",
        (item_id, customer_id, new_place)
    )
    return new_place


def update_waitlist(item_id: str = None):
    """
    removes person at position 1 and shifts everyone else down by 1
    """
    cur.execute(
        "DELETE FROM waitlist WHERE item_id = ? AND place_in_line = 1",
        (item_id,)
    )
    cur.execute(
        "UPDATE waitlist SET place_in_line = place_in_line - 1 WHERE item_id = ?",
        (item_id,)
    )


def return_item(item_id: str = None, customer_id: str = None):
    """
    moves a rental from rental to rental_history with return_date = today
    """
    cur.execute(
        "SELECT item_id, customer_id, rental_date, due_date FROM rental "
        "WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )
    row = cur.fetchone()
    if row is None:
        return

    today = date.today()

    cur.execute(
        "INSERT INTO rental_history (item_id, customer_id, rental_date, due_date, return_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(row[0]).strip(), str(row[1]).strip(), str(row[2]), str(row[3]), str(today))
    )

    cur.execute(
        "DELETE FROM rental WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )


def grant_extension(item_id: str = None, customer_id: str = None):
    """
    adds 14 days to the due date
    """
    cur.execute(
        "UPDATE rental SET due_date = DATE_ADD(due_date, INTERVAL 14 DAY) "
        "WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )


def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    returns a list of Item objects matching the filters
    """
    query = (
        "SELECT i_item_id, i_product_name, i_brand, i_category, i_manufact, "
        "i_current_price, YEAR(i_rec_start_date), i_num_owned FROM item WHERE 1=1"
    )
    params = []
    op = "LIKE" if use_patterns else "="

    if filter_attributes.item_id is not None:
        query += f" AND i_item_id {op} ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.product_name is not None:
        query += f" AND i_product_name {op} ?"
        params.append(filter_attributes.product_name)
    if filter_attributes.brand is not None:
        query += f" AND i_brand {op} ?"
        params.append(filter_attributes.brand)
    if filter_attributes.category is not None:
        query += f" AND i_category {op} ?"
        params.append(filter_attributes.category)
    if filter_attributes.manufact is not None:
        query += f" AND i_manufact {op} ?"
        params.append(filter_attributes.manufact)
    if filter_attributes.current_price != -1:
        query += " AND i_current_price = ?"
        params.append(filter_attributes.current_price)
    if filter_attributes.num_owned != -1:
        query += " AND i_num_owned = ?"
        params.append(filter_attributes.num_owned)
    if filter_attributes.start_year != -1:
        query += " AND YEAR(i_rec_start_date) = ?"
        params.append(filter_attributes.start_year)

    if min_price != -1:
        query += " AND i_current_price >= ?"
        params.append(min_price)
    if max_price != -1:
        query += " AND i_current_price <= ?"
        params.append(max_price)
    if min_start_year != -1:
        query += " AND YEAR(i_rec_start_date) >= ?"
        params.append(min_start_year)
    if max_start_year != -1:
        query += " AND YEAR(i_rec_start_date) <= ?"
        params.append(max_start_year)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(Item(
            item_id=row[0].strip() if row[0] else None,
            product_name=row[1].strip() if row[1] else None,
            brand=row[2].strip() if row[2] else None,
            category=row[3].strip() if row[3] else None,
            manufact=row[4].strip() if row[4] else None,
            current_price=float(row[5]) if row[5] is not None else -1,
            start_year=int(row[6]) if row[6] is not None else -1,
            num_owned=int(row[7]) if row[7] is not None else -1,
        ))
    return results


def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    returns a filtered list of Customer objects
    """
    query = (
        "SELECT c.c_customer_id, c.c_first_name, c.c_last_name, c.c_email_address, "
        "ca.ca_street_number, ca.ca_street_name, ca.ca_city, ca.ca_state, ca.ca_zip "
        "FROM customer c "
        "LEFT JOIN customer_address ca ON c.c_current_addr_sk = ca.ca_address_sk "
        "WHERE 1=1"
    )
    params = []
    op = "LIKE" if use_patterns else "="

    if filter_attributes.customer_id is not None:
        query += f" AND c.c_customer_id {op} ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.name is not None:
        query += f" AND CONCAT(TRIM(c.c_first_name), ' ', TRIM(c.c_last_name)) {op} ?"
        params.append(filter_attributes.name)
    if filter_attributes.email is not None:
        query += f" AND c.c_email_address {op} ?"
        params.append(filter_attributes.email)
    if filter_attributes.address is not None:
        query += (
            f" AND CONCAT(TRIM(ca.ca_street_number), ' ', TRIM(ca.ca_street_name), ', ', "
            f"TRIM(ca.ca_city), ', ', TRIM(ca.ca_state), ' ', TRIM(ca.ca_zip)) {op} ?"
        )
        params.append(filter_attributes.address)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    results = []
    for row in rows:
        cid = row[0].strip() if row[0] else None
        first = row[1].strip() if row[1] else ""
        last = row[2].strip() if row[2] else ""
        name = f"{first} {last}".strip()
        email = row[3].strip() if row[3] else None

        street_num = row[4].strip() if row[4] else ""
        street_name = row[5].strip() if row[5] else ""
        city = row[6].strip() if row[6] else ""
        state = row[7].strip() if row[7] else ""
        zip_code = row[8].strip() if row[8] else ""
        address = f"{street_num} {street_name}, {city}, {state} {zip_code}".strip()

        results.append(Customer(
            customer_id=cid,
            name=name if name else None,
            address=address if address.replace(",", "").strip() else None,
            email=email,
        ))
    return results


def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    returns a filtered list of Rental objects
    """
    query = "SELECT item_id, customer_id, rental_date, due_date FROM rental WHERE 1=1"
    params = []

    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.rental_date is not None:
        query += " AND rental_date = ?"
        params.append(filter_attributes.rental_date)
    if filter_attributes.due_date is not None:
        query += " AND due_date = ?"
        params.append(filter_attributes.due_date)

    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(Rental(
            item_id=str(row[0]).strip() if row[0] else None,
            customer_id=str(row[1]).strip() if row[1] else None,
            rental_date=str(row[2]) if row[2] else None,
            due_date=str(row[3]) if row[3] else None,
        ))
    return results


def get_filtered_rental_histories(filter_attributes: RentalHistory = None,
                                  min_rental_date: str = None,
                                  max_rental_date: str = None,
                                  min_due_date: str = None,
                                  max_due_date: str = None,
                                  min_return_date: str = None,
                                  max_return_date: str = None) -> list[RentalHistory]:
    """
    returns a filtered list of RentalHistory objects
    """
    query = (
        "SELECT item_id, customer_id, rental_date, due_date, return_date "
        "FROM rental_history WHERE 1=1"
    )
    params = []

    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.rental_date is not None:
        query += " AND rental_date = ?"
        params.append(filter_attributes.rental_date)
    if filter_attributes.due_date is not None:
        query += " AND due_date = ?"
        params.append(filter_attributes.due_date)
    if filter_attributes.return_date is not None:
        query += " AND return_date = ?"
        params.append(filter_attributes.return_date)

    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)
    if min_return_date is not None:
        query += " AND return_date >= ?"
        params.append(min_return_date)
    if max_return_date is not None:
        query += " AND return_date <= ?"
        params.append(max_return_date)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(RentalHistory(
            item_id=str(row[0]).strip() if row[0] else None,
            customer_id=str(row[1]).strip() if row[1] else None,
            rental_date=str(row[2]) if row[2] else None,
            due_date=str(row[3]) if row[3] else None,
            return_date=str(row[4]) if row[4] else None,
        ))
    return results


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    returns a filtered list of Waitlist objects
    """
    query = "SELECT item_id, customer_id, place_in_line FROM waitlist WHERE 1=1"
    params = []

    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.place_in_line != -1:
        query += " AND place_in_line = ?"
        params.append(filter_attributes.place_in_line)

    if min_place_in_line != -1:
        query += " AND place_in_line >= ?"
        params.append(min_place_in_line)
    if max_place_in_line != -1:
        query += " AND place_in_line <= ?"
        params.append(max_place_in_line)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(Waitlist(
            item_id=str(row[0]).strip() if row[0] else None,
            customer_id=str(row[1]).strip() if row[1] else None,
            place_in_line=int(row[2]) if row[2] is not None else -1,
        ))
    return results


def number_in_stock(item_id: str = None) -> int:
    """
    returns num_owned = active rentals or -1 if item doesn't exist
    """
    cur.execute("SELECT i_num_owned FROM item WHERE i_item_id = ?", (item_id,))
    row = cur.fetchone()
    if row is None:
        return -1

    num_owned = row[0]

    cur.execute("SELECT COUNT(*) FROM rental WHERE item_id = ?", (item_id,))
    active_rentals = cur.fetchone()[0]

    return num_owned - active_rentals


def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    returns the customer's place_in_line or -1 if not on waitlist
    """
    cur.execute(
        "SELECT place_in_line FROM waitlist WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )
    row = cur.fetchone()
    if row is None:
        return -1
    return row[0]


def line_length(item_id: str = None) -> int:
    """
    returns how many people are on the waitlist for this item
    """
    cur.execute("SELECT COUNT(*) FROM waitlist WHERE item_id = ?", (item_id,))
    return cur.fetchone()[0]


def save_changes():
    conn.commit()


def close_connection():
    cur.close()
    conn.close()
