from test import BinarySearchTree
import json

with open('ErasTourDict.json') as file:
    data = json.load(file)


class Node:
    def __init__(self, date, left=None, right=None):
        self.date = date
        self.left = left
        self.right = right


class BinarySearchTree:
    def __init__(self):
        self.root = None
    
    def insert(self, date):
        if self.root is None:
            self.root = Node(date)
        else:
            self._insert(date, self.root)

    def _insert(self, date, node):
        if date < node.date:
            if node.left is None:
                node.left = Node(date)
            else:
                self._insert(date, node.left)
        elif date > node.date:
            if node.right is None:
                node.right = Node(date)
            else:
                self._insert(date, node.right)
        else:
            raise ValueError("Date already exists in the tree")
        

concert_date = "June 10, 2023"

bst = BinarySearchTree()
for date in data.keys():
    bst.insert(date)
    node = bst.root
    while node is not None:
        if concert_date < node.date:
            node = node.left
        elif concert_date > node.date:
            node = node.right
        else:
            openers = data[node.date]["openers"]

print(data)