"""Этот модуль отвечает за симулятор сервера на n-ное кол-во тэгов. (Пример: python server_sim.py 10
opc.tcp://localhost:4840/freeopcua/server/)"""

import sys
import time
from random import choice, randint
from typing import Any, Dict, Tuple

import numpy as np
import opcua
from opcua import Server, ua

sys.path.insert(0, "..")
STORAGE_FILE = "storage.txt"  # тэги на удаление
RENAME_STORAGE_FILE = "rename_storage.txt"  # тэги на переименование
server = Server()
mytags: Dict[str, Tuple[opcua.Node, str]] = {}
myobj: opcua.Node = None
running = True


def create_tags(num: int, myobj: opcua.Node) -> Dict[str, Tuple[opcua.Node, str]]:
    types = ["Double", "Int", "Boolean", "ByteString", "XmlElement"]
    tags = {}
    for elem in range(num):
        tag_type = choice(types)
        tag_name = f"{tag_type}_tag{elem}"
        if tag_type == "Double":
            myvar = myobj.add_variable(
                f"ns=2;s={tag_name}", tag_name, 0.0
            )  # float в питоне обладает точностью типа double из C (если интерпретатор
            # - CPython)
        elif tag_type == "Int":
            myvar = myobj.add_variable(f"ns=2;s={tag_name}", tag_name, 0)

        elif tag_type == "ByteString":
            value = b"0"
            myvar = myobj.add_variable(f"ns=2;s={tag_name}", tag_name, value)
        elif tag_type == "XmlElement":
            value = ua.XmlElement("<value>random</value>")
            myvar = myobj.add_variable(f"ns=2;s={tag_name}", tag_name, value)

        else:  # tag_type == 'Boolean'
            myvar = myobj.add_variable(f"ns=2;s={tag_name}", tag_name, False)
        myvar.set_writable()

        # access_level = ua.AccessLevel.CurrentRead | ua.AccessLevel.CurrentWrite
        # myvar.set_attribute(ua.AttributeIds.UserAccessLevel, ua.DataValue(ua.Variant(access_level)))
        print(tag_name)
        tags[tag_name] = (myvar, tag_type)
    return tags


def delete_tag_from_server(tag_name: str) -> bool:
    """Удаление тега из OPC UA сервера"""
    if tag_name in mytags:
        node, _ = mytags.pop(tag_name)
        try:
            server.delete_nodes([node])
            return True
        except Exception as e:
            print(f"Error deleting node {tag_name}: {e}")
            return False
    return False


def rename_tag_on_server(old_name: str, new_name: str) -> bool:
    """Переименование тега на OPC UA сервера"""
    if old_name in mytags:
        node, _ = mytags[old_name]
        try:
            # server.delete_nodes([node])
            new_browse_name = ua.QualifiedName(new_name, node.nodeid.NamespaceIndex)
            node.set_attribute(
                ua.AttributeIds.BrowseName, ua.DataValue(new_browse_name)
            )

            new_display_name = ua.LocalizedText(new_name)
            node.set_attribute(
                ua.AttributeIds.DisplayName, ua.DataValue(new_display_name)
            )
            # node.get_browse_name() =
            mytags[new_name] = mytags.pop(old_name)
            return True
        except Exception as e:
            print(f"Error renaming node {old_name}: {e}")
            return False
    return False


def check_file(file):
    try:
        with open(file, "r+") as f:
            lines = f.readlines()
            if not lines:
                return  # Файл пуст
            if file == "storage.txt":  # len(words) == 1:  # значит в строке одно имя
                # Берём первое имя
                first_name = lines[0].strip()
                # print(f"Обработано имя: {first_name}")
                delete_tag_from_server(first_name)  # вызов нужной функции
            elif (
                file == "rename_storage.txt"
            ):  # len(words) == 2: # значит в строке записано два имени (для переименования)
                words = lines[0].split()
                old_name = words[0]
                new_name = words[1]
                rename_tag_on_server(old_name, new_name)

            # Удаляем обработанное имя из файла
            remaining_names = lines[1:]
            f.seek(0)
            f.writelines(remaining_names)
            f.truncate()  # Обрезаем файл до новой длины

    except FileNotFoundError:
        print("Файл пока не создан")
    except Exception as e:
        print(f"Ошибка: {e}")


def start_server(
    num: int, url: str
) -> (
    None
):  # принимать уникальный url (при запуске файла) или порт и потом передавать его
    global myobj, mytags, running

    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    # server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_endpoint(url)

    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    objects = server.get_objects_node()

    myobj = objects.add_object(idx, "MyObject")
    # myobj.set_attribute(ua.AttributeIds.UserWriteMask, ua.DataValue(ua.Variant(ua.WriteAccess.All)))
    # print(type(myobj))
    mytags = create_tags(num, myobj)

    server.start()
    # x = 0
    try:
        while True:
            check_file(STORAGE_FILE)  # проверяем файл для удаления тэгов
            check_file(RENAME_STORAGE_FILE)  # проверяем файл для переименования тэгов
            for my_var, tag_type in mytags.values():
                if tag_type == "Double":
                    value = np.random.uniform(1.5, 150.65)
                    my_var.set_value(value)
                elif tag_type == "Int":
                    value = randint(1, 150)
                    my_var.set_value(value)
                elif tag_type == "XmlElement":
                    value = ua.XmlElement(f"<result>{randint(0, 150)}</result>")
                    my_var.set_value(value)
                elif tag_type == "ByteString":
                    value = bytes([randint(0, 255)]) + bytes([randint(0, 255)])
                    my_var.set_value(value)
                else:  # tag_type == 'Boolean'
                    value = choice([True, False])
                    my_var.set_value(value)
                # print(my_var.get_value())
            time.sleep(1)
    finally:
        server.stop()
        print("server stop")


if __name__ == "__main__":
    tag_num = int(sys.argv[1])
    server_url = str(sys.argv[2])
    start_server(tag_num, server_url)
