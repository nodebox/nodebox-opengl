import sys
import unittest

sys.path.append('..')

from nodebox.graphics import Layer

class LayerTest(unittest.TestCase):
    
    def test_layer_at(self):
        # Nest three layers in eachother
        grandparent_layer = Layer(0, 0, 30, 100)
        parent_layer = Layer(0, 0, 20, 100)
        child_layer = Layer(0, 0, 10, 100)
        # Name the layers (easier for debugging)
        grandparent_layer.name = "grandparent"
        parent_layer.name = "parent"
        child_layer.name = "child"
        # Setup hierarchy
        grandparent_layer.append(parent_layer)
        parent_layer.append(child_layer)
        # layer_at should return the deepest layer
        self.assertEquals(child_layer, grandparent_layer.layer_at(5, 5))
        # Test edges
        self.assertEquals(child_layer, grandparent_layer.layer_at(0, 0))
        self.assertEquals(child_layer, grandparent_layer.layer_at(10, 100))
        self.assertEquals(grandparent_layer, grandparent_layer.layer_at(30, 100))
        self.assertEquals(None, grandparent_layer.layer_at(5, -1))
        self.assertEquals(None, grandparent_layer.layer_at(31, 5))
        
if __name__=='__main__':
    unittest.main()