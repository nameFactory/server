# server

Server for _nameFactory_ project made using Python 3 and Flask.

## Installation

**Note**: consider installing it in virtual environment.

Install dependencies by running `pip install -r requirements.txt`.

Add descriptions of the names (as unicode-escaped strings) to the `desc.json` file. Example:

```json
{
    "Name1": "Desc1",
    "Name2": "Desc2"
}
```

To initialize database, run `python init_db.py`. **Warning**: it will remove existing database.

## Running

For development purposes running `./server.py` should be sufficient.
