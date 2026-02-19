import sqlite3
import re
import os

def parse_taxon_line(line, current_rank):
    """Parses a line to extract taxon name, author, and notes, given its rank."""
    # Remove the rank keyword from the start of the line and strip whitespace
    content = line.replace(current_rank, '', 1).strip()
    
    name = None
    author = None
    notes = None

    # Pattern to capture Name, Author/Year
    # e.g., "Trilobita Walch, 1771", "Eodiscida Kobayashi, 1939", "Calodiscidae Kobayashi, 1943 (6 genera, 55 species)"
    # This regex is an attempt to be more general.
    # It tries to find a name, followed by an optional author/year, and then optional notes in parentheses.
    
    # Try to match a common pattern: Name Author, Year (Notes)
    match = re.match(r"^(.*?)(?:(?:\s+([A-Z][A-Za-z\s&,]+,\s\d{4}[a-z]?|Öpik,\s\d{4}|Černyševa,\s\d{4}))\s*)?(\(.*\))?$", content)

    if match:
        name_part = match.group(1).strip()
        author_part = match.group(2)
        notes_part = match.group(3)

        # Refine name and author extraction
        if author_part:
            name = name_part
            author = author_part.strip()
        else:
            # If no explicit author_part was matched by the regex group(2), 
            # check if the last two words of name_part could be an author/year.
            name_parts_split = name_part.rsplit(' ', 2)
            if len(name_parts_split) >= 2 and re.match(r'\d{4}[a-z]?', name_parts_split[-1]): # Last part is year
                potential_author = name_parts_split[-2]
                if re.match(r'[A-Z][a-zA-Z\s\.]*', potential_author): # Second to last part is potential author name
                    name = ' '.join(name_parts_split[:-2]).strip()
                    author = f"{potential_author}, {name_parts_split[-1]}".strip()
                else:
                    name = name_part
            else:
                name = name_part
        
        if notes_part:
            notes = notes_part.strip()

    else: # Fallback for lines that don't fit the pattern well
        name = content.split('(')[0].strip()
        notes_match = re.search(r'(\(.*\))', content)
        notes = notes_match.group(1).strip() if notes_match else None
        # Attempt to find author in the remaining content if not already found
        if not author:
            # Simple heuristic for author at the end of the name before notes
            potential_author_year_match = re.search(r'([A-Z][A-Za-z\s&,]+,\s\d{4}[a-z]?|Öpik,\s\d{4}|Černyševa,\s\d{4})$', name)
            if potential_author_year_match:
                author = potential_author_year_match.group(0).strip()
                name = name.replace(author, '').strip()

    # Clean up name from potential stray numbers/superscripts at the end
    name = re.sub(r'[\d\s]+$', '', name).strip()
    return name, author, notes

def populate_database_from_ranks(file_path, db_path):
    """Parses the rank-prefixed text file and populates the taxonomic_ranks table."""
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear the table before populating
    cursor.execute("DELETE FROM taxonomic_ranks;")
    conn.commit()
    print("Cleared existing data from taxonomic_ranks table.")

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Define the hierarchy of ranks, including 'Class'
    rank_hierarchy = ['Class', 'Order', 'Suborder', 'Superfamily', 'Family']
    
    # last_seen_id stores the ID of the last seen taxon for each rank
    last_seen_id = {}
    
    # --- Step 1: Insert "Class Trilobita" as the root node ---
    class_line = lines[0].strip() # Assuming "Class Trilobita..." is the first line
    
    # Parse the Class line
    class_name_match = re.match(r"Class\s+([A-Za-z\s]+)\s+([A-Z][A-Za-z\s&,]+,\s\d{4}[a-z]?|Öpik,\s\d{4}|Černyševa,\s\d{4})?", class_line)
    
    trilobita_name = "Trilobita"
    trilobita_author = None
    trilobita_notes = None

    if class_name_match:
        trilobita_name_raw = class_name_match.group(1).strip()
        trilobita_name = re.sub(r'[\d\s]+$', '', trilobita_name_raw).strip() # Remove numbers like 177112
        trilobita_author = class_name_match.group(2).strip() if class_name_match.group(2) else None
        
    try:
        cursor.execute(
            "INSERT INTO taxonomic_ranks (name, rank, parent_id, author, notes) VALUES (?, ?, ?, ?, ?)",
            (trilobita_name, 'Class', None, trilobita_author, trilobita_notes)
        )
        class_trilobita_id = cursor.lastrowid
        last_seen_id['Class'] = class_trilobita_id
        print(f"Inserted: Class '{trilobita_name}' (ID: {class_trilobita_id}, Parent ID: NULL)")
    except sqlite3.Error as e:
        print(f"Error inserting Class '{trilobita_name}': {e}")
        return # Stop if root cannot be inserted

    # --- Step 2: Process the rest of the lines ---
    for line in lines[1:]: # Start from the second line
        line = line.strip()
        if not line:
            continue

        current_rank = None
        for rank_name in rank_hierarchy[1:]: # Check for Order, Suborder, Superfamily, Family
            if line.startswith(rank_name):
                current_rank = rank_name
                break
        
        if not current_rank:
            print(f"Skipping unhandled line (no recognized rank prefix): {line}")
            continue

        name, author, notes = parse_taxon_line(line, current_rank)

        # Determine parent_id
        parent_id = None
        current_rank_index = rank_hierarchy.index(current_rank)
        
        # Find the parent's rank by going up the hierarchy
        for i in range(current_rank_index - 1, -1, -1):
            potential_parent_rank = rank_hierarchy[i]
            if potential_parent_rank in last_seen_id:
                parent_id = last_seen_id[potential_parent_rank]
                break
        
        # Insert into database
        try:
            cursor.execute(
                "INSERT INTO taxonomic_ranks (name, rank, parent_id, author, notes) VALUES (?, ?, ?, ?, ?)",
                (name, current_rank, parent_id, author, notes)
            )
            new_id = cursor.lastrowid
            
            # Update the last seen ID for the current rank
            last_seen_id[current_rank] = new_id
            
            # Invalidate the last seen IDs for all lower ranks
            for i in range(current_rank_index + 1, len(rank_hierarchy)):
                lower_rank = rank_hierarchy[i]
                if lower_rank in last_seen_id:
                    del last_seen_id[lower_rank]
            
            print(f"Inserted: {current_rank} '{name}' (ID: {new_id}, Parent ID: {parent_id or 'NULL'})")

        except sqlite3.Error as e:
            print(f"Error inserting {current_rank} '{name}': {e}")

    conn.commit()
    conn.close()
    print("Database population complete.")

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')
    txt_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'adrain2011.txt')
    populate_database_from_ranks(txt_file_path, db_path)
