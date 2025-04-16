import sqlite3
import os
import re
import logging
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)

class QueryProcessor:
    def __init__(self):
        self.temp_db_path = None
        self.conn = None
        
    def setup_temp_db(self, sql_file_path):
        """Set up a temporary SQLite database from a SQL file"""
        try:
            # Create a temporary database file
            temp_db = NamedTemporaryFile(suffix='.db', delete=False)
            self.temp_db_path = temp_db.name
            temp_db.close()
            
            # Connect to the database
            self.conn = sqlite3.connect(self.temp_db_path)
            cursor = self.conn.cursor()
            
            # Read and execute the SQL file
            with open(sql_file_path, 'r') as f:
                sql_script = f.read()
                
            # Split the script by semicolons and execute each statement
            # This is a simple approach and might not work for complex SQL files
            sql_statements = sql_script.split(';')
            for statement in sql_statements:
                if statement.strip():
                    try:
                        cursor.execute(statement)
                    except sqlite3.Error as e:
                        logger.warning(f"Error executing SQL statement: {str(e)}")
                        # Continue with other statements even if one fails
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting up temporary database: {str(e)}")
            self.cleanup()
            return False
    
    def parse_sql_file(self, sql_file_path):
        """Parse a SQL file to extract schema information"""
        try:
            with open(sql_file_path, 'r') as f:
                content = f.read()
            
            # We'll extract all CREATE TABLE statements as our schema context
            # This is a simplified approach - for complex schemas you might want
            # to use a proper SQL parser
            create_table_pattern = r'CREATE\s+TABLE\s+[^;]+;'
            create_tables = re.findall(create_table_pattern, content, re.IGNORECASE | re.DOTALL)
            
            schema_context = "\n".join(create_tables)
            return schema_context
        except Exception as e:
            logger.error(f"Error parsing SQL file: {str(e)}")
            return ""
    
    def execute_query(self, query):
        """Execute a SQL query against the temporary database"""
        if not self.conn:
            return {"error": "Database not initialized. Please upload a SQL file first."}
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            columns = [description[0] for description in cursor.description] if cursor.description else []
            results = cursor.fetchall()
            
            return {
                "columns": columns,
                "rows": results,
                "rowCount": len(results)
            }
        except sqlite3.Error as e:
            return {"error": f"SQL error: {str(e)}"}
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
            
            if self.temp_db_path and os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
                self.temp_db_path = None
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")