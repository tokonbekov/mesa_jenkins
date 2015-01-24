


class Bisector:
    """tracks down bisections for a set of tests"""
    def __init__(self):
        # has a test list, a single range, and a base_revision to
        # check.
        self.target_tests = []
        self.bisect_project = None
        self.revision_range = []
        self.base_revisions = None

        # after bisect, this list grows
        self.generated_bisections = []

        # if bisect identifies a revision, this list grows.  Contains
        # PiglitTest objects
        self.bisected_tests = []
        self.bisected_revision

        
    def Bisect(self):
        """performs a bisection.  can generate more Bisector objects if tests
        split on the bisection."""
        pass
    

class BisectorSet:
    """Contains a set of Bisector objects.  Iterates on the set,
    appending new Bisector objects with subsets of tests when necessary"""
    #piglit_range, mesa_range, waffle_range, and drm_range.  


class PiglitTest:
    """Represents a single test.  Has the primary arch that will be
    tested, and a list of other arches that are expected to be caused
    by the same revision"""
    preferred_arches = ["m64", "m32"]
    preferred_platforms = ["hswgt3e", "hswgt2", "hswgt1", "ivbgt2",
                           "ivbgt1"] # ...
    def __init__(self):
        self.test_name = None
        self.test_arch = None
        self.other_arches = []
        self.diff_text = None

    def AddTest(self, test, diff_blob):
        # assert test name is the same
        # choose the preferred arch
        # put secondary arch in the list

class GTestFile:
    """Parses a file, generates a list of PiglitTest objects that
    failed"""
    
class TestLister:
    """reads xml files and generates a set of PiglitTest objects"""
    def __init__(self, bad_dir):
        # self.test_map is keyed by test name, value is PiglitTest
        pass
    


# instantiate test lister, generate PiglitTest objects

# create bisectorset with all the test objects

# run a build on first piglit rev, to identify which tests are from
# piglit.  make a list of bisector objects for them.

# repeat for mesa, waffle, drm

# 
