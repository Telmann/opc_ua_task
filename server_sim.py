"""
Этот модуль отвечает за симулятор сервера на n-ное кол-во тэгов. (Пример: python server_sim.py 100)
"""

import sys
import time
from random import choice, randint
from typing import Any, Dict, Tuple

import numpy as np
import opcua
from opcua import Server, ua

sys.path.insert(0, "..")


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
        tags[tag_name] = (myvar, tag_type)
    return tags


def start_server(num: int) -> None:
    # setup
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")

    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    objects = server.get_objects_node()

    myobj = objects.add_object(idx, "MyObject")
    # print(type(myobj))
    mytags = create_tags(num, myobj)

    server.start()

    try:
        while True:
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
            time.sleep(0.25)

    finally:
        server.stop()
        print("server stop")


if __name__ == "__main__":
    tag_num = int(sys.argv[1])
    start_server(tag_num)
