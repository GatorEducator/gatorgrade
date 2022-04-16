# Import the necessary libraries
import os

# Directories to ignore 
ignore_directory_list = [".git", ".github", ".pytest_cache", "__pycache__"]
# Files to ignore
ignore_files_list = [
    ".gitignore", 
    "pyproject.toml",
     ".DS_Store", 
     ".markdownlint.json", 
     "README.md", 
     "gatorgrader.yml", 
     "build.gradle",
     "__init__.py"]

# Final paths to write to the gatorgrade.yml file
final_paths = []

for dirpath, dirnames, filenames in os.walk("."):
    """Generate the file names in a directory tree by walking the three top-down"""

    # Remove directories from directory lists based on ignore_directory_list
    for name in ignore_directory_list:
        if name in dirnames:
            dirnames.remove(name)

    # Remove files from files lists based on ignore_files_list
    for name in ignore_files_list:
        if name in filenames:
            filenames.remove(name)

    # Print path to all filenames
    for filename in filenames:
        # Join the directory path with the filename
        # print(os.path.join(dirpath, filename))
        final_paths.append(os.path.join(dirpath, filename))

    
# Create a new YAML file 
gatorgrader_file = open("gatorgrade.yml", "w")

# Write to the file the name of the paths
for path in final_paths:
    without_dot = path.strip("./")
    gatorgrader_file.write(f"{without_dot}:\n\t--description:\n\tcheck: MatchFileFragment\n\toptions:\n\t\tcount:\n\t\tfragment: TODO\n\t\texact: {True}")
    # gatorgrader_file.write(f"{without_dot}:\n")
    gatorgrader_file.write("\n")
    gatorgrader_file.write("\n")

# Close the file
gatorgrader_file.close()