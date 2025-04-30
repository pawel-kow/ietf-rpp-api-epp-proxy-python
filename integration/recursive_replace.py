import json
import copy

def replace_placeholders(data_structure, replacements):
  """
  Recursively traverses a dictionary or list (representing JSON) and replaces
  placeholders in string values.

  Placeholders are expected in the format {key}, where 'key' corresponds to a
  key in the 'replacements' dictionary.

  Args:
    data_structure: A dictionary or list (potentially nested) where replacements
                    should occur. This structure will be modified in-place.
    replacements: A dictionary where keys are the placeholder names (without
                  curly braces) and values are the strings to substitute.

  Returns:
    The modified data_structure (although modification happens in-place).

  Raises:
    TypeError: If the input `data_structure` is not a dict or list, or if
               `replacements` is not a dict.
  """
  if not isinstance(replacements, dict):
      raise TypeError("Replacements argument must be a dictionary.")

  # --- Inner recursive helper function ---
  def _recursive_replace(item):
    if isinstance(item, dict):
      # Iterate over a copy of keys if modifying dict during iteration
      # (though here we modify values, which is generally safe)
      for key, value in item.items():
        item[key] = _recursive_replace(value) # Recurse/process value
      return item # Return the modified dictionary

    elif isinstance(item, list):
      for i, element in enumerate(item):
        item[i] = _recursive_replace(element) # Recurse/process element
      return item # Return the modified list

    elif isinstance(item, str):
      modified_string = item
      for key, value in replacements.items():
        placeholder = f"{{{key}}}"
        # Ensure replacement value is also a string
        replacement_value_str = str(value)
        modified_string = modified_string.replace(placeholder, replacement_value_str)
      return modified_string # Return the modified string

    else:
      # For other data types (int, float, bool, None, etc.), return as is
      return item
  # --- End of inner function ---

  if not isinstance(data_structure, (dict, list)):
      raise TypeError("Input data_structure must be a dictionary or a list.")

  # Start the recursive replacement process
  # Although the function modifies in-place, we return the reference for convenience
  return _recursive_replace(data_structure)

if __name__ == "__main__":
    # --- Example Usage ---

    # 1. Sample JSON-like structure (as a Python dict)
    json_data = {
        "name": "Project {project_name}",
        "version": "1.0",
        "description": "This project uses {language} for backend.",
        "components": [
            {
                "type": "database",
                "url": "db://{db_host}:{db_port}/{db_name}",
                "user": "{db_user}"
            },
            {
                "type": "api",
                "path": "/api/v1",
                "message": "Welcome, {user}!"
            },
            "Configuration path: /etc/{project_name}/config"
        ],
        "metadata": {
            "deployed_by": "{user}",
            "environment": "{env}",
            "details": {
                "nested_value": "Value is {some_value}"
            }
        },
        "enabled": True,
        "port_number": 8080
    }

    # 2. Replacements dictionary
    replacement_values = {
        "project_name": "Phoenix",
        "language": "Python",
        "db_host": "localhost",
        "db_port": 5432,
        "db_name": "phoenix_db",
        "db_user": "admin",
        "user": "Alice",
        "env": "production",
        "some_value": "important data"
        # Note: Placeholders not in this dict won't be replaced.
    }

    # --- Important Note on In-Place Modification ---
    # The function modifies the original dictionary. If you need to preserve the
    # original, create a deep copy first.
    json_data_copy = copy.deepcopy(json_data)

    # 3. Call the function
    print("--- Original Data ---")
    print(json.dumps(json_data, indent=2))

    modified_data = replace_placeholders(json_data_copy, replacement_values)

    print("\n--- Replacements ---")
    print(replacement_values)

    print("\n--- Modified Data ---")
    print(json.dumps(modified_data, indent=2))

    # Verify the original is unchanged if you used deepcopy
    # print("\n--- Original Data (should be unchanged) ---")
    # print(json.dumps(json_data, indent=2))

    # Example with invalid input type for data_structure
    try:
        replace_placeholders("just a string", replacement_values)
    except TypeError as e:
        print(f"\nCaught expected error for invalid data_structure type: {e}")

    # Example with invalid input type for replacements
    try:
        replace_placeholders({}, ["not", "a", "dict"])
    except TypeError as e:
        print(f"\nCaught expected error for invalid replacements type: {e}")