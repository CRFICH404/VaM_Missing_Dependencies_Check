import os
import json
import re
from zipfile import ZipFile


def get_var_names(root):
    var_names = []
    for root ,dirs, files in os.walk(root):
        for file in files:
            if file.endswith(".var"):
                var_names.append(file)
    return var_names

def crop_file_extensions(var_names):
    print("Cropping file extensions...")
    var_names_no_ext = []
    for var_name in var_names:
        replace_last_part_in_name(var_name, '')
    return var_names_no_ext

def get_all_dependencies(var_names, root):
    print("Getting all dependencies...")
    pattern = r'\.min\d+$'
    dependencies = {".latest": set(), ".version": set(), ".min": set()}
    for var_name in var_names:
        var_path = os.path.join(root, var_name)
        print(var_path)
        try:
            print("Unzipping " + var_path)
            with ZipFile(var_path, "r") as zipped_file:
                contents = zipped_file.namelist()
                if "meta.json" in contents:
                    meta = zipped_file.open("meta.json")
                    try:
                        json_data = json.load(meta)
                    except json.decoder.JSONDecodeError:
                        print(var_path + " has corrupt JSON")
                    try:
                        for dependency in json_data["dependencies"]:

                            if bool(re.search(pattern, dependency)):
                                if dependency not in dependencies[".min"]:
                                    print(dependency + " added to \".min\" list")
                                    dependencies[".min"].add(dependency)

                            elif dependency.endswith(".latest"):
                                if dependency not in dependencies[".latest"]:
                                    print(dependency + " added to \".latest\" list")
                                    dependencies[".latest"].add(dependency)

                            else:
                                if dependency not in dependencies[".version"]:
                                    print(dependency + " added to \".versions\" list")
                                    dependencies[".version"].add(dependency)

                    except KeyError:
                        print(var_path + " has no dependencies")
                else:
                    print(var_path + " has no meta.json")

        except FileNotFoundError:
            print(f"Zip file {var_name} not found")

    return dependencies

def get_min_dependency_version(dep_name):
    dep_name = dep_name.split(".")
    return dep_name[-1][3:]

def replace_last_part_in_name(dep_name, replace_with):
    new_name = ''
    dep_name = dep_name.split(".")
    dep_name = dep_name[:-1]
    for part in dep_name:
        if new_name == '':
            new_name = part
        else:
            new_name += '.' + part

    return new_name + replace_with

def find_matching_string (string_list, base_string, min_version):
    pattern = create_regex_pattern_for_search_higher_versions(base_string, min_version)
    return [s for s in string_list if re.search(pattern, s)]

def clear_min_list (dependencies):
    print("Clearing \".min\" list...")
    cleared_min_list = set()
    for dependency in dependencies[".min"]:
        min_version = get_min_dependency_version(dependency)
        latest_version = replace_last_part_in_name(dependency, '.latest')
        if latest_version not in dependencies[".latest"]:
            matching_strings = find_matching_string(dependencies[".version"], replace_last_part_in_name(dependency, ""), min_version )
            if not matching_strings:
                cleared_min_list.add(dependency)
            else:
                print(f"{dependency} not a dependency: found in \".version\" list")
                print(matching_strings)
        else:
            print(f"{dependency} not a dependency found in \".latest\" list")

    return cleared_min_list

def clear_version_list (dependencies):
    print("Clearing \".version\" list...")
    cleared_version_list = set()
    for dependency in dependencies[".version"]:
        latest_version = replace_last_part_in_name(dependency, ".latest")
        print(latest_version)
        if latest_version not in dependencies[".latest"]:
            cleared_version_list.add(dependency)
        else:
            print(f"{dependency} not a dependency")
    return cleared_version_list

def create_regex_pattern_for_search_higher_versions (base_string, min_number):
    escaped_base = re.escape(base_string)
    min_string = str(min_number)
    number_pattern = r'\.' + ''.join([f'([{d}-9]|[1-9]\\d+)' if d != '0' else '\\d+' for d in min_string]) + '$'
    return escaped_base + number_pattern

def clear_not_tied_to_version_dependencies(dependencies):
    print("Clearing not tied to version dependencies...")
    cleared_dependencies = {".latest": dependencies[".latest"].copy(), ".version": clear_version_list(dependencies), ".min": clear_min_list(dependencies)}
    return cleared_dependencies

def look_for_missing_dependencies(root):
    print("Looking for missing dependencies...")
    var_names = get_var_names(root)
    existing_var_names_no_extension = crop_file_extensions(var_names)
    all_dependencies = get_all_dependencies(var_names, root)
    cleared_dependencies = clear_not_tied_to_version_dependencies(all_dependencies)
    print("Before clear: ", all_dependencies['.latest'].__len__(), all_dependencies['.version'].__len__(), all_dependencies['.min'].__len__())
    print("After clear: ",cleared_dependencies['.latest'].__len__(), cleared_dependencies['.version'].__len__(), cleared_dependencies['.min'].__len__())
    missing_dependencies = set()
    for dep_type in cleared_dependencies:
        if cleared_dependencies[dep_type].__len__() > 0:
            for dependency in cleared_dependencies[dep_type]:



def check_for_repeated_installed_dependencies(root):
    print("Checking for repeated dependencies...")
    for var_name in get_var_names(root):
        ...

def check_for_outdated_dependencies(root):
    print("Checking for outdated dependencies...")
    var_names = get_var_names(root)

if __name__ == "__main__":
    isRunning = True
    path = "G:\\VaM_1.20.77.9\\AddonPackages"

    if not os.path.exists(path):
        print("Directory '" + path + "' not found.")
        exit(1)

    while isRunning:
        print("_________________________________________________MENU_________________________________________________")
        print("(1) Check for missing dependencies")
        print("(2) Check for repeated installed dependencies")
        print("(3) Check for outdated dependencies")
        print("(4) Exit")
        print("_______________________________________________________________________________________________________")
        user_input = input("Type your choice: ")
        match user_input:
            case "1":
                look_for_missing_dependencies(path)
            case "2":
                check_for_repeated_installed_dependencies(path)
            case "3":
                check_for_outdated_dependencies(path)
            case "4":
                isRunning = False
