import os
import re
import json
import sys
from zipfile import ZipFile

def print_asset_list (asset_list):
    total_count = 0
    for author in asset_list:
        print(
            "_______________________________________________________________________________________________________________")
        print(f"\nAuthor:     {author}\n")
        for file in asset_list[author]:
            total_count += len(asset_list[author][file])
            print(f"    {file}: {asset_list[author][file]}")
    print(f"\nTotal Files: {total_count}\n")

def print_asset_list_for_search (asset_list):
    print(
        "_______________________________________________________________________________________________________________")
    total_count = 0
    for author in sorted(asset_list):
        for file in sorted(asset_list[author]):
            for version in asset_list[author][file]:
                total_count += 1
                print(f"{author}.{file}.{version}")
    print(f"\nTotal Files: {total_count}\n")

def add_asset (data, author_name, asset_name, asset_version, corrupt_data):
    print(f"Adding asset {author_name}.{asset_name}.{asset_version}")
    try:
        if author_name not in data:
            data[author_name] = {}
        if asset_name not in data[author_name]:
            data[author_name][asset_name] = []
        if asset_version not in data[author_name][asset_name]:
            data[author_name][asset_name].append(asset_version)
    except KeyError:
        corrupt_data.append(f"{author_name}.{asset_name}.{asset_version}")

def add_dep_asset (data, author_name, asset_name, asset_version, corrupt_data):
    print(f"Adding asset {author_name}.{asset_name}.{asset_version}")
    try:
        if author_name not in data:
            data[author_name] = {}
        if asset_name not in data[author_name]:
            data[author_name][asset_name] = {"latest" : bool(), "version" : [], "min" : []}
        if asset_version == 'latest':
            data[author_name][asset_name][asset_version] = True
        elif re.search(r"min\d+$", asset_version):
            if asset_version not in data[author_name][asset_name]['min']:
                data[author_name][asset_name]['min'].append(asset_version)
        else:
            version = int(asset_version)
            if version not in data[author_name][asset_name]['version']:
                data[author_name][asset_name]['version'].append(version)
    except KeyError:
        corrupt_data.append(f"{author_name}.{asset_name}.{asset_version}")

def get_minimal_version (data):
    return int(data[3:])

def get_var_names(root):
    var_names = {}
    faulty_var_names = []
    for root ,dirs, files in os.walk(root):
        for file in files:
            if file.endswith(".var"):
                name = str(file).replace(".var", "").lstrip().rstrip()
                name = name.split('.')
                length = len(name)
                if length >= 2:
                    author_name = name[0]
                    asset_name = name[1]
                    asset_version = name[2]
                    add_asset(var_names, author_name, asset_name, asset_version, faulty_var_names)
                if length == 1:
                    author_name = name[0]
                    asset_name = name[0]
                    asset_version = name[1]
                    add_asset(var_names, author_name, asset_name, asset_version, faulty_var_names)

    print_asset_list(var_names)

    return var_names, faulty_var_names

def crop_file_extensions(var_names):
    print("Cropping file extensions...")
    var_names_no_ext = []
    for var_name in var_names:
        var_names_no_ext.append(replace_last_part_in_name(var_name, ''))
    return var_names_no_ext

def get_all_dependencies(var_names, root):
    print("Getting all dependencies...")
    dependencies = {}
    dep_corrupt_data = []
    for author in var_names:
        for file in var_names[author]:
            if var_names[author][file].__len__() > 1:
                var_names[author][file] = sorted(var_names[author][file])
            var_path = str(os.path.join(root, f"{author}.{file}.{var_names[author][file][-1]}.var"))
            print(var_path)
            try:
                print("Unzipping " + var_path)
                with ZipFile(var_path, "r") as zipped_file:
                    contents = zipped_file.namelist()
                    if "meta.json" in contents:
                        with zipped_file.open("meta.json") as meta:
                            try:
                                json_data = json.load(meta)
                                try:
                                    for dependency in json_data["dependencies"]:
                                        dependency = str(dependency).lstrip().rstrip()
                                        dep_author, dep_name, dep_version = str(dependency).lstrip().rstrip().split(".")
                                        add_dep_asset(dependencies, dep_author, dep_name, dep_version, dep_corrupt_data)
                                except KeyError:
                                    print(var_path + " has no dependencies")
                            except json.decoder.JSONDecodeError:
                                print(var_path + " has corrupt JSON")
                    else:
                        print(var_path + " has no meta.json")
            except FileNotFoundError:
                print(f"Zip file {author}.{file}.{var_names[author][file][-1]} not found")
    print_asset_list(dependencies)
    return dependencies, dep_corrupt_data

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

def clear_dependencies_from_repeated_versions(dependencies):
    print("Clearing dependencies list...")
    cleared_dependencies = {}
    faulty_dependencies = []
    for author in dependencies:
        for file in dependencies[author]:
            if dependencies[author][file]["min"].__len__() > 0:
                add_asset(cleared_dependencies, author, file, sorted(dependencies[author][file]["min"])[-1], faulty_dependencies)
            elif dependencies[author][file]["latest"]:
                add_asset(cleared_dependencies, author, file, 'latest', faulty_dependencies)
            else:
                add_asset(cleared_dependencies, author, file, sorted(dependencies[author][file]["version"])[-1], faulty_dependencies)

    return cleared_dependencies, faulty_dependencies

def print_faulty_var_names (faulty_var_names):
    if faulty_var_names.__len__() > 0:
        print(
            "_______________________________________________________________________________________________________________")
        print("Faulty var names:")
        for data in faulty_var_names:
            print(data)
        print(
            "_______________________________________________________________________________________________________________")

def search_for_missing_dependencies(var_names, dependencies):
    print("Searching for missing dependencies...")
    missing_dependencies = {}
    corrupt_data = []
    for author in dependencies:
        for file in dependencies[author]:
            try:
                if author not in var_names or file not in var_names[author]:
                    if author not in var_names:
                        print(f"Author: {author} was not found...")
                    else:
                        print(f"File: {file} was not found...")
                    add_asset(missing_dependencies, author, file, dependencies[author][file][0], corrupt_data)
                    continue

                if dependencies[author][file][0] == "latest":
                    if var_names[author][file].__len__() == 0:
                        print(f"No corresponding versions were found for {author}.{file}.latest")
                        add_asset(missing_dependencies, author, file, dependencies[author][file][0], corrupt_data)

                elif type(dependencies[author][file][0]) is type(int()):
                    if str(dependencies[author][file][0]) not in var_names[author][file]:
                        print(f"No corresponding version was found for {author}.{file}.{dependencies[author][file][0]}")
                        add_asset(missing_dependencies, author, file, dependencies[author][file][0], corrupt_data)

                else:
                    filtered_versions = sorted(set(filter(lambda version: int(version) >= get_minimal_version(dependencies[author][file][0]), var_names[author][file])))
                    if filtered_versions.__len__() == 0:
                        add_asset(missing_dependencies, author, file, dependencies[author][file][0], corrupt_data)

            except KeyError:
                corrupt_data.append(f"{author}.{file}.{var_names[author][file][0]}")
    return missing_dependencies, corrupt_data


def get_missing_dependencies(root):
    print("Looking for missing dependencies...")
    existing_var_names, faulty_data = get_var_names(root)
    print_faulty_var_names(faulty_data)
    all_dependencies, dep_faulty_data = get_all_dependencies(existing_var_names, root)
    print_faulty_var_names(dep_faulty_data)
    cleared_dependencies, cleared_dep_faulty_data = clear_dependencies_from_repeated_versions(all_dependencies)
    print_asset_list(cleared_dependencies)
    print_faulty_var_names(cleared_dep_faulty_data)
    missing_dependencies, corrupt_missing_dep = search_for_missing_dependencies(existing_var_names, cleared_dependencies)
    print_faulty_var_names(corrupt_missing_dep)
    return missing_dependencies

def check_for_repeated_installed_dependencies(root):
    print("Checking for repeated dependencies...")
    installed_var_names, faulty_var_names = get_var_names(root)
    print_faulty_var_names(faulty_var_names)
    repeating_vars = {}
    faulty_dependencies = []
    for author in installed_var_names:
        for file in installed_var_names[author]:
            if installed_var_names[author][file].__len__() > 1:
                for version in sorted(installed_var_names[author][file]):
                    add_asset(repeating_vars, author, file, version, faulty_dependencies)
    print_faulty_var_names(faulty_dependencies)
    return repeating_vars

def check_for_outdated_dependencies(root):
    print("Checking for outdated dependencies...")
    var_names = get_var_names(root)

def create_main_menu (root):
    return dict(enumerate([{'function' : find_missing_dependencies, 'string' : 'Find missing dependencies', 'func_input' : root},
                           {'function' : find_repeated_installed_dependencies, 'string' : 'Find repeated installed dependencies', 'func_input' : root},
                           {'function' : remove_repeated_dependencies, 'string' : 'Remove repeated dependencies', 'func_input' : root},
                           {'function' : exit_program, 'string' : 'Exit', 'func_input' : None}], start=1))

def create_print_result_submenu (results):
    return dict(enumerate([{'function': print_asset_list, 'string': 'Print organized by author, file', 'func_input': results},
                           {'function': print_asset_list_for_search, 'string': 'Print formatted for search', 'func_input': results}], start=1))

def create_remove_repeated_dependencies_submenu (results):
    return dict(enumerate([{'function': remove_all_repeated_dependencies, 'string': 'Remove all repeated versions but latest version', 'func_input': results},
                           {'function': safe_remove_repeated_dependencies, 'string': 'Safe remove only known to be \".latest\" dependencies', 'func_input': results}], start=1))

def print_menu (menu_items):
    print("_________________________________________________MENU_________________________________________________\n")
    for k, function in menu_items.items():
        print(f"({k}) {function['string']}")
    print("_______________________________________________________________________________________________________")

def run_submenu (menu_items):
    print_menu(menu_items)
    while True:
        selection = int(input("Please select an option: "))
        if selection not in menu_items:
            print("Please select a valid option.")
            continue
        selected_value = menu_items[selection]['function']
        if menu_items[selection]['func_input'] is None:
            selected_value()
            break
        else:
            selected_value(menu_items[selection]['func_input'])
            break

def run_menu (menu_items):
    while True:
        print_menu(menu_items)
        selection = int(input("Please select an option: "))
        if selection not in menu_items:
            print("Please select a valid option.")
            continue
        selected_value = menu_items[selection]['function']
        if menu_items[selection]['func_input'] is None:
            selected_value()
        else:
            selected_value(menu_items[selection]['func_input'])

def find_missing_dependencies(root):
    missing_dep = get_missing_dependencies(root)
    if input("Print missing dependencies? (y/n): ").lower() == "y":
        run_menu(create_print_result_submenu(missing_dep))

def find_repeated_installed_dependencies(root):
    repeated_installed_vars = check_for_repeated_installed_dependencies(root)
    if input("Print repeated dependencies? (y/n): ").lower() == "y":
        run_submenu(create_print_result_submenu(repeated_installed_vars))

def remove_repeated_dependencies(root):
    repeated_installed_vars = check_for_repeated_installed_dependencies(root)
    run_submenu(create_remove_repeated_dependencies_submenu(repeated_installed_vars))

def safe_remove_repeated_dependencies(repeated_versions):
    ...

def remove_all_repeated_dependencies(repeated_versions):
    ...

def exit_program():
    print("Exiting...")
    sys.exit()

def main():
    # isRunning = True
    path = "G:\\VaM_1.20.77.9\\AddonPackages"

    if not os.path.exists(path):
        print("Directory '" + path + "' not found.")
        sys.exit(1)

    run_menu(create_main_menu(path))


if __name__ == "__main__":
    main()