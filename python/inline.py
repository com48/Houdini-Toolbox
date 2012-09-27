"""This module contains functions designed to extend the Houdini Object Model
(HOM) through the use of the inlinecpp module and regular Python.

The functions in this module are not mean to be called directly.  This module
uses Python decorators to attach the functions to the corresponding HOM classes
and modules they are meant to extend.

"""
__author__ = "Graham Thompson"
__email__ = "captainhammy@gmail.com"

# Houdini Imports
import hou
import inlinecpp

def addToModule(module):
    """This function decorator adds the function to a specified module.

    Args:
        module : (module)
            The HOM module to extend.

    Returns:
        func
            The original module object is returned.

    Raises: N/A

    """

    def decorator(f):
        # Simply add the function to the module object.
        setattr(module, f.__name__, f)
        return f

    return decorator


def addToClass(*args, **kwargs):
    """This function decorator adds the function to specified classes,
    optionally specifying a different function name.

    Args:
        *args:
            One of more HOM classes to extend.
        **kwargs:
            name: Set a specific name for the unbound method.

    Returns:
        func
            The original function object is returned, unmodified.

    Raises: N/A

    """
    import types

    def decorator(f):
        # Iterate over each class passed in.
        for target_class in args:
            # Check if we tried to set the method name.  If so, use the
            # specified value.
            if "name" in kwargs:
                func_name = kwargs["name"]
            # If not, use the original name.
            else:
                func_name = f.__name__

            # Create a new unbound method.
            method = types.MethodType(f, None, target_class)

            # Attach the method to the class.
            setattr(target_class, func_name, method)

        # We don't really care about modifying the function so just return
        # it.
        return f

    return decorator


#-----------------------------------------------------------------------------
# Name: _buildCStringArray
#
# Args:
#    values : (list)
#        A list of strings.
#
# Returns: c_char_p_Array
#              A ctypes char * array.
#
# Raises: N/A
#
# Desc: Convert a list of strings to a ctypes char * array.
#-----------------------------------------------------------------------------
def _buildCStringArray(values):
    import ctypes
    arr = (ctypes.c_char_p * len(values))()
    arr[:] = values

    return arr


#-----------------------------------------------------------------------------
# Name: _buildCFloatArray
#
# Args:
#     values : (list)
#         A list of floats.
#
# Returns: c_float_Array
#              A ctypes float array.
#
# Raises: N/A
#
# Desc: Convert a list of numbers to a ctypes float array.
#-----------------------------------------------------------------------------
def _buildCFloatArray(values):
    import ctypes
    arr = (ctypes.c_float * len(values))()
    arr[:] = values

    return arr


#-----------------------------------------------------------------------------
# Name: _buildBoundingBox
#
# Args:
#     bounds : (hutil.cppinline.BoundingBox)
#         An inlinecpp bounding box object.
#
# Returns: hou.BoundingBox
#              A HOM style bounding box.
#
# Raises: N/A
#
# Desc: Convert an inlinecpp returned bounding box to a hou.BoundingBox.
#-----------------------------------------------------------------------------
def _buildBoundingBox(bounds):
    # Construct a new HOM bounding box from the name members of the class.
    return hou.BoundingBox(
        bounds.xmin,
        bounds.ymin,
        bounds.zmin,
        bounds.xmax,
        bounds.ymax,
        bounds.zmax
    )


#-----------------------------------------------------------------------------
# Name: _getPointsFromList
#
# Args:
#     geometry : (hou.Geometry)
#         The geometry the points belongs to.
#     point_list : (list|tuple)
#         A list of integers representing point numbers.
#
# Returns: tuple
#              A tuple of hou.Point objects.
#
# Raises: N/A
#
# Desc: Convert a list of point numbers to hou.Point objects.
#-----------------------------------------------------------------------------
def _getPointsFromList(geometry, point_list):
    # Return a empty tuple if the point list is empty.
    if not point_list:
        return ()

    # Convert the list of integers to a space separated string.
    point_str = ' '.join([str(i) for i in point_list])

    # Glob for the specified points.
    return geometry.globPoints(point_str)


#-----------------------------------------------------------------------------
# Name: _getPrimsFromList
#
# Args:
#     geometry : (hou.Geometry)
#         The geometry the primitives belongs to.
#     prim_list : (list|tuple)
#         A list of integers representing primitive numbers.
#
# Returns: tuple
#              A tuple of hou.Prim objects.
#
# Raises: N/A
#
# Desc: Convert a list of primitive numbers to hou.Prim objects.
#-----------------------------------------------------------------------------
def _getPrimsFromList(geometry, prim_list):
    # Return a empty tuple if the prim list is empty.
    if not prim_list:
        return ()

    # Convert the list of integers to a space separated string.
    prim_str = ' '.join([str(i) for i in prim_list])

    # Glob for the specified prims.
    return geometry.globPrims(prim_str)


#-----------------------------------------------------------------------------
# Name: _getNodesFromPaths
#
# Args:
#     paths : (list|tuple)
#         A list of strings node paths.
#
# Returns: tuple
#              A tuple of hou.Node objects.
#
# Raises: N/A
#
# Desc: Convert a list of string paths to hou.Node objects.
#-----------------------------------------------------------------------------
def _getNodesFromPaths(paths):
    return tuple([hou.node(path) for path in paths if path])


#-----------------------------------------------------------------------------
# Name: _getTimeFromOpInfo
#
# Args:
#     node : (hou.Node)
#         A Houdini node.
#     prefix : (str)
#         An opinfo line prefix containing a date and time.
#
# Returns: datetime.datetime|None
#              The datetime matching the opinfo line, if it exists, otherwise
#              None.
#
# Raises: N/A
#
# Desc: Extract a datetime.datetime from the opinfo of a node.
#-----------------------------------------------------------------------------
def _getTimeFromOpInfo(node, prefix):
    import datetime

    # Get the operator info and split info rows.
    info = hou.hscript("opinfo -n {0}".format(node.path()))[0].split('\n')

    # Check each row.
    for row in info:
        #  If the row doesn't start with our prefix, ignore it.
        if not row.startswith(prefix):
            continue

        # Strip the prefix and any leading whitespace.
        time_str = row[len(prefix):].strip()

        # Construct a datetime object.
        return datetime.datetime.strptime(time_str, "%d %b %Y %I:%M %p")

    return None


_cpp_methods = inlinecpp.createLibrary(
    "cpp_methods",
    acquire_hom_lock=True,
    catch_crashes=True,
    includes="""
#include <GA/GA_AttributeRefMap.h>
#include <GEO/GEO_Face.h>
#include <GQ/GQ_Detail.h>
#include <GU/GU_Detail.h>
#include <OP/OP_Director.h>
#include <OP/OP_Node.h>
#include <OP/OP_OTLManager.h>
#include <PRM/PRM_Parm.h>
#include <UT/UT_WorkArgs.h>
""",
    structs=[
        ("IntArray", "*i"),
        ("StringArray", "**c"),
        ("StringTuple", "*StringArray"),
        ("VertexMap", (("prims", "*i"), ("indices", "*i"))),
        ("Position3D", (("x", "d"), ("y", "d"), ("z", "d"))),
        ("BoundingBox", (
            ("xmin", "d"),
            ("ymin", "d"),
            ("zmin", "d"),
            ("xmax", "d"),
            ("ymax", "d"),
            ("zmax", "d")
            )
        ),
    ],
    function_sources=[
"""
int
addNumToRange(int num, int sec, void *data)
{
    std::vector<int>            *values;

    // Get the passed in vector.
    values = (std::vector<int> *)data;

    // Add the number to it.
    values->push_back(num);

    // Return 1 to keep going.
    return 1;
}
""",

"""
IntArray
expandRange(const char *pattern)
{
    std::vector<int>            values;

    UT_String                   range;
    UT_WorkArgs                 tokens;

    range = pattern;

    // Tokenize the pattern to split out the groups of ranges.
    range.tokenize(tokens, ' ');

    for (int i=0; i<tokens.getArgc(); ++i)
    {
        // Get the current range.
        UT_String tmp = tokens[i];

        // Add all the values in the range to the list.
        tmp.traversePattern(-1, &values, addNumToRange);
    }

    return values;
}
""",

"""
void
sortAlongAxis(GU_Detail *gdp, int mode, int axis)
{
    // Sort primitives.
    if (mode)
    {
        gdp->sortPrimitiveList(axis);
    }
    // Sort points.
    else
    {
        gdp->sortPointList(axis);
    }
}
""",

"""
void
sortByValues(GU_Detail *gdp, int mode, float *values)
{
    // Sort primitives.
    if (mode)
    {
        gdp->sortPrimitiveList(values);
    }
    // Sort points.
    else
    {
        gdp->sortPointList(values);
    }
}
""",

"""
void
sortListRandomly(GU_Detail *gdp, int mode, float seed)
{
    // Sort primitives.
    if (mode)
    {
        gdp->sortPrimitiveList(seed);
    }
    // Sort points.
    else
    {
        gdp->sortPointList(seed);
    }
}
""",

"""
void
shiftList(GU_Detail *gdp, int mode, int offset)
{
    // Sort primitives.
    if (mode)
    {
        gdp->shiftPrimitiveList(offset);
    }
    // Sort points.
    else
    {
        gdp->shiftPointList(offset);
    }
}
""",

"""
void
reverseList(GU_Detail *gdp, int mode)
{
    // Sort primitives.
    if (mode)
    {
        gdp->reversePrimitiveList();
    }
    // Sort points.
    else
    {
        gdp->reversePointList();
    }
}
""",

"""
void
proximityToList(GU_Detail *gdp, int mode, const UT_Vector3D *point)
{
    UT_Vector3                  pos(*point);

    // Sort primitives.
    if (mode)
    {
        gdp->proximityToPrimitiveList(pos);
    }
    // Sort points.
    else
    {
        gdp->proximityToPointList(pos);
    }
}
""",

"""
void
sortByVertexOrder(GU_Detail *gdp)
{
    gdp->sortByVertexOrder();
}
""",

"""
void
setIcon(OP_Operator *op, const char *icon_name)
{
    op->setIconName(icon_name);
}
""",

"""
void
setDefaultIcon(OP_Operator *op)
{
    op->setDefaultIconName();
}
""",

"""
bool
isSubnetType(OP_Operator *op)
{
    return op->getIsPrimarySubnetType();
}
""",

"""
bool
isPython(OP_Operator *op)
{
    return op->getScriptIsPython();
}
""",

"""
int
createPoint(GU_Detail *gdp, UT_Vector3D *position)
{
    GA_Offset                   ptOff;

    // Add a new point.
    ptOff = gdp->appendPointOffset();

    // Set the position for the point.
    gdp->setPos3(ptOff, *position);

    // Return the point number.
    return gdp->pointIndex(ptOff);
}
""",

"""
IntArray
createPoints(GU_Detail *gdp, int count)
{
    std::vector<int>            point_nums;

    GA_Offset                   ptOff;

    for (int i=0; i < count; ++i)
    {
        ptOff = gdp->appendPointOffset();
        point_nums.push_back(gdp->pointIndex(ptOff));
    }

    return point_nums;
}
""",

"""
void
setVarmap(GU_Detail *gdp, const char **strings, int num_strings)
{
    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    UT_String                   value;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_DETAIL, "varmap");

    // If it doesn't exist, add it.
    if (attrib_gah.isInvalid())
    {
        attrib_gah = gdp->createStringAttribute(GA_ATTRIB_DETAIL, "varmap");
    }

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    // Resize the tuple to our needed size.
    s_t->setTupleSize(attrib, num_strings);

    // Iterate over all the strings to assign.
    for (int i=0; i < num_strings; ++i)
    {
        // Get the string.
        value = strings[i];
        // Add it to the tuple at this point.
        s_t->setString(attrib, GA_Offset(0), value, i);
    }
}
""",

"""
void
addVariableName(GU_Detail *gdp, const char *attrib_name, const char *var_name)
{
    gdp->addVariableName(attrib_name, var_name);
}
""",

"""
void
removeVariableName(GU_Detail *gdp, const char *var_name)
{
    gdp->removeVariableName(var_name);
}
""",

"""
bool
renameAttribute(GU_Detail *gdp,
                int attrib_type,
                const char *from_name,
                const char *to_name)
{
    GA_AttributeOwner           owner;

    // Convert the int value to the attribute owner type.
    owner = static_cast<GA_AttributeOwner>(attrib_type);

    // Rename the attribute.
    return gdp->renameAttribute(owner, GA_SCOPE_PUBLIC, from_name, to_name);
}
""",

"""
int
findPrimitiveByName(const GU_Detail *gdp,
                    const char *name_to_match,
                    const char *name_attribute,
                    int match_number)
{
    const GEO_Primitive         *prim;

    // Try to find a primitive.
    prim = gdp->findPrimitiveByName(name_to_match,
                                    GEO_PrimTypeCompat::GEOPRIMALL,
                                    name_attribute,
                                    match_number);

    // If one was found, return its number.
    if (prim)
    {
        return prim->getNum();
    }

    // Return -1 to indicate that no prim was found.
    return -1;
}
""",

"""
IntArray
findAllPrimitivesByName(const GU_Detail *gdp,
                        const char *name_to_match,
                        const char *name_attribute)
{
    std::vector<int>            prim_nums;

    GEO_ConstPrimitivePtrArray  prims;
    GEO_ConstPrimitivePtrArray::const_iterator prims_it;

    // Try to find all the primitives given the name.
    gdp->findAllPrimitivesByName(prims,
                                 name_to_match,
                                 GEO_PrimTypeCompat::GEOPRIMALL,
                                 name_attribute);

    // Add any found prims to the array.
    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back((*prims_it)->getNum());
    }

    return prim_nums;
}
""",

"""
void
copyPointAttributeValues(GU_Detail *dest_gdp,
                         int dest_pt,
                         const GU_Detail *src_gdp,
                         int src_pt,
                         const char **attribute_names,
                         int num_attribs)
{
    GA_Offset                   srcOff, destOff;

    GA_ROAttributeRef           src_gah;
    GA_RWAttributeRef           dest_gah;

    const GA_Attribute          *attr;

    UT_String                   attr_name;

    // Build an attribute reference map between the geometry.
    GA_AttributeRefMap hmap(*dest_gdp, src_gdp);

    // Iterate over all the attribute names.
    for (int i=0; i < num_attribs; ++i)
    {
        // Get the attribute name.
        attr_name = attribute_names[i];

        // Get the attribute reference from the source geometry.
        src_gah = src_gdp->findPointAttribute(attr_name);
        if (src_gah.isValid())
        {
            // Get the actual attribute.
            attr = src_gah.getAttribute();

            // Try to find the same attribute on the destination geometry.
            dest_gah = dest_gdp->findPointAttrib(*attr);

            // If it doesn't exist, create it.
            if (dest_gah.isInvalid())
            {
                dest_gah = dest_gdp->addPointAttrib(attr);
            }

            // Add a mapping between the source and dest attributes.
            hmap.append(dest_gah.getAttribute(), attr);
        }
    }

    // Get the point offsets.
    srcOff = src_gdp->pointOffset(src_pt);
    destOff = src_gdp->pointOffset(dest_pt);

    // Copy the attribute value.
    hmap.copyValue(GA_ATTRIB_POINT, destOff, GA_ATTRIB_POINT, srcOff);
}
""",

"""
void
copyPrimAttributeValues(GU_Detail *dest_gdp,
                        int dest_pr,
                        const GU_Detail *src_gdp,
                        int src_pr,
                        const char **attribute_names,
                        int num_attribs)
{
    GA_Offset                   srcOff, destOff;

    GA_ROAttributeRef           src_gah;
    GA_RWAttributeRef           dest_gah;

    const GA_Attribute          *attr;

    UT_String                   attr_name;

    // Build an attribute reference map between the geometry.
    GA_AttributeRefMap hmap(*dest_gdp, src_gdp);

    // Iterate over all the attribute names.
    for (int i=0; i < num_attribs; ++i)
    {
        // Get the attribute name.
        attr_name = attribute_names[i];

        // Get the attribute reference from the source geometry.
        src_gah = src_gdp->findPrimitiveAttribute(attr_name);
        if (src_gah.isValid())
        {
            // Get the actual attribute.
            attr = src_gah.getAttribute();

            // Try to find the same attribute on the destination geometry.
            dest_gah = dest_gdp->findPrimAttrib(*attr);

            // If it doesn't exist, create it.
            if (dest_gah.isInvalid())
            {
                dest_gah = dest_gdp->addPrimAttrib(attr);
            }

            // Add a mapping between the source and dest attributes.
            hmap.append(dest_gah.getAttribute(), attr);
        }
    }

    // Get the primitive offsets.
    srcOff = src_gdp->primitiveOffset(src_pr);
    destOff = src_gdp->primitiveOffset(dest_pr);

    // Copy the attribute value.
    hmap.copyValue(GA_ATTRIB_PRIMITIVE,
                   destOff,
                   GA_ATTRIB_PRIMITIVE,
                   srcOff);
}
""",

"""
IntArray
pointAdjacentPolygons(GU_Detail *gdp, int prim_num)
{
    std::vector<int>            prim_nums;

    GA_Offset                   primOff;
    GA_OffsetArray              prims;
    GA_OffsetArray::const_iterator prims_it;

    // Find the offset for this primitive.
    primOff = gdp->primitiveOffset(prim_num);

    // Get a list of point adjacent polygons.
    gdp->getPointAdjacentPolygons(prims, primOff);

    // Add the adjacent prim numbers to the list.
    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back(gdp->primitiveIndex(*prims_it));
    }

    return prim_nums;
}
""",

"""
IntArray
edgeAdjacentPolygons(GU_Detail *gdp, int prim_num)
{
    std::vector<int>            prim_nums;

    GA_Offset                   primOff;
    GA_OffsetArray              prims;
    GA_OffsetArray::const_iterator prims_it;

    // Find the offset for this primitive.
    primOff = gdp->primitiveOffset(prim_num);

    // Get a list of edge adjacent polygons.
    gdp->getEdgeAdjacentPolygons(prims, primOff);

    // Add the adjacent prim numbers to the list.
    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back(gdp->primitiveIndex(*prims_it));
    }

    return prim_nums;
}
""",

"""
IntArray
connectedPrims(const GU_Detail *gdp, int pt_num)
{
    std::vector<int>    prim_nums;

    GA_Offset           ptOff;
    GA_OffsetArray      prims;
    GA_OffsetArray::const_iterator prims_it;

    // Get the selected point offset.
    ptOff = gdp->pointOffset(pt_num);

    // Get all the primitives referencing this point.
    gdp->getPrimitivesReferencingPoint(prims, ptOff);

    // Add all the primitive numbers to the list.
    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back(gdp->primitiveIndex(*prims_it));
    }

    return prim_nums;
}
""",

"""
IntArray
connectedPoints(const GU_Detail *gdp, int pt_num)
{
    std::vector<int>            pt_nums;

    GA_Offset                   ptOff;
    GA_OffsetArray              prims;

    GA_Range                    pt_range;

    const GEO_Primitive         *prim;

    // The list of primitives in the geometry.
    const GA_PrimitiveList &prim_list = gdp->getPrimitiveList();

    ptOff = gdp->pointOffset(pt_num);

    // Get the primitives referencing the point.
    gdp->getPrimitivesReferencingPoint(prims, ptOff);

    // Build a range for those primitives.
    GA_Range pr_range(gdp->getPrimitiveMap(), prims);

    for (GA_Iterator pr_it(pr_range.begin()); !pr_it.atEnd(); ++pr_it)
    {
        prim = (GEO_Primitive *)prim_list.get(*pr_it);

        // Get the points referenced by the vertices of the primitive.
        pt_range = prim->getPointRange();

        for (GA_Iterator pt_it(pt_range.begin()); !pt_it.atEnd(); ++pt_it)
        {
            // Build an edge between the source point and this point on the
            // primitive.
            GA_Edge edge(ptOff, *pt_it);
            // If there is an edge between those 2 points, add the point
            // to the list.
            if (prim->hasEdge(edge))
            {
                pt_nums.push_back(gdp->pointIndex(*pt_it));
            }
        }
    }

    return pt_nums;
}
""",

"""
VertexMap
referencingVertices(const GU_Detail *gdp, int pt_num)
{
    std::vector<int>            prim_indices, vert_indices;

    GA_Index                    primIdx;
    GA_Offset                   ptOff, primOff, vtxOff;
    GA_OffsetArray              vertices;

    const GA_Primitive          *prim;

    GA_OffsetArray::const_iterator vert_it;

    ptOff = gdp->pointOffset(pt_num);
    gdp->getVerticesReferencingPoint(vertices, ptOff);

    const GA_PrimitiveList &prim_list = gdp->getPrimitiveList();

    for (vert_it = vertices.begin(); !vert_it.atEnd(); ++vert_it)
    {
        vtxOff = *vert_it;

        primOff = gdp->vertexPrimitive(vtxOff);
        primIdx = gdp->primitiveIndex(primOff);
        prim = prim_list.get(primOff);

        for (unsigned i=0; i < prim->getVertexCount(); ++i)
        {
            if (prim->getVertexOffset(i) == vtxOff)
            {
                prim_indices.push_back(primIdx);
                vert_indices.push_back(i);
            }
        }
    }

    VertexMap vert_map;
    vert_map.prims.set(prim_indices);
    vert_map.indices.set(vert_indices);

    return vert_map;
}
""",

"""
StringArray
primStringAttribValues(const GU_Detail *gdp, const char *attrib_name)
{
    std::vector<std::string>    result;

    const GA_Attribute          *attrib;
    GA_ROAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_PRIMITIVE, attrib_name);

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    for (GA_Iterator it(gdp->getPrimitiveRange()); !it.atEnd(); ++it)
    {
        result.push_back(s_t->getString(attrib, *it, 0));
    }

    return result;
}
""",

"""
void
setPrimStringAttribValues(GU_Detail *gdp,
                          const char *attrib_name,
                          const char **values,
                          int num_values)
{
    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_PRIMITIVE, attrib_name);

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    int i = 0;
    for (GA_Iterator it(gdp->getPrimitiveRange()); !it.atEnd(); ++it)
    {
        s_t->setString(attrib, *it, values[i], 0);
        i++;
    }
}
""",

"""
int
setSharedPrimStringAttrib(GU_Detail *gdp,
                          const char *attrib_name,
                          const char *value,
                          const char *group_name=0)
{
    GA_PrimitiveGroup           *group = 0;

    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Find the primitive group if necessary.
    if (group_name)
    {
        group = gdp->findPrimitiveGroup(group_name);
    }

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_PRIMITIVE, attrib_name);

    // If it doesn't exist, return 1 to indicate we have an invalid attribute.
    if (attrib_gah.isInvalid())
    {
        return 1;
    }

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    if (group)
    {
        // Set all the primitives in the group to the value.
        s_t->setString(attrib, GA_Range(*group), value, 0);
    }
    else
    {
        // Set all the primitives in the detail to the value.
        s_t->setString(attrib, gdp->getPrimitiveRange(), value, 0);
    }

    // Return 0 to indicate success.
    return 0;
}
""",

"""
StringArray
pointStringAttribValues(const GU_Detail *gdp, const char *attrib_name)
{
    std::vector<std::string>    result;

    const GA_Attribute          *attrib;
    GA_ROAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_POINT, attrib_name);

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    for (GA_Iterator it(gdp->getPointRange()); !it.atEnd(); ++it)
    {
        result.push_back(s_t->getString(attrib, *it, 0));
    }

    return result;
}
""",

"""
void
setPointStringAttribValues(GU_Detail *gdp,
                           const char *attrib_name,
                           const char **values,
                           int num_values)
{
    int                         i=0;

    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_POINT, attrib_name);

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    for (GA_Iterator it(gdp->getPointRange()); !it.atEnd(); ++it)
    {
        s_t->setString(attrib, *it, values[i], 0);
        i++;
    }
}
""",

"""
int
setSharedPointStringAttrib(GU_Detail *gdp,
                           const char *attrib_name,
                           const char *value,
                           const char *group_name=0)
{
    GA_PointGroup               *group = 0;

    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Find the point group if necessary.
    if (group_name)
    {
        group = gdp->findPointGroup(group_name);
    }

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_POINT, attrib_name);

    // If it doesn't exist, return 1 to indicate we have an invalid attribute.
    if (attrib_gah.isInvalid())
    {
        return 1;
    }

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    if (group)
    {
        // Set all the points in the group to the value.
        s_t->setString(attrib, GA_Range(*group), value, 0);
    }
    else
    {
        // Set all the points in the detail to the value.
        s_t->setString(attrib, gdp->getPointRange(), value, 0);
    }

    // Return 0 to indicate success.
    return 0;
}
""",

"""
bool
hasEdge(const GU_Detail *gdp,
        unsigned prim_num,
        unsigned pt_num1,
        unsigned pt_num2)
{
    GA_Offset                   primOff, ptOff1, ptOff2;

    const GEO_Face              *face;

    primOff = gdp->primitiveOffset(prim_num);

    ptOff1 = gdp->pointOffset(pt_num1);
    ptOff2 = gdp->pointOffset(pt_num2);

    face = (GEO_Face *)gdp->getPrimitiveList().get(primOff);

    // Build an edge between the the two points.
    GA_Edge edge(ptOff1, ptOff2);

    return face->hasEdge(edge);
}
""",

"""
void
insertVertex(GU_Detail *gdp,
             unsigned prim_num,
             unsigned pt_num,
             unsigned idx)
{
    GA_Offset                   ptOff, primOff;

    GEO_Face                    *face;

    ptOff = gdp->pointOffset(pt_num);
    primOff = gdp->primitiveOffset(prim_num);

    face = (GEO_Face *)gdp->getPrimitiveList().get(primOff);

    face->insertVertex(ptOff, idx);
}
""",

"""
void
deleteVertex(GU_Detail *gdp, unsigned prim_num, unsigned idx)
{
    GA_Offset                   primOff;

    GEO_Face                    *face;

    primOff = gdp->primitiveOffset(prim_num);

    face = (GEO_Face *)gdp->getPrimitiveList().get(primOff);

    face->deleteVertex(idx);
}
""",

"""
void
setPoint(GU_Detail *gdp, unsigned prim_num, unsigned idx, unsigned pt_num)
{
    GA_Offset                   ptOff, primOff;

    GA_Primitive                *prim;

    ptOff = gdp->pointOffset(pt_num);
    primOff = gdp->primitiveOffset(prim_num);

    prim = (GA_Primitive *)gdp->getPrimitiveList().get(primOff);

    prim->setPointOffset(idx, ptOff);
}
""",

"""
Position3D
baryCenter(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    const GEO_Primitive         *prim;

    UT_Vector3                  center;

    Position3D                  pos;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GEO_Primitive *)gdp->getPrimitiveList().get(primOff);

    center = prim->baryCenter();

    pos.x = center.x();
    pos.y = center.y();
    pos.z = center.z();

    return pos;
}
""",

"""
double
primitiveArea(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    const GA_Primitive         *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GA_Primitive *)gdp->getPrimitiveList().get(primOff);

    return prim->calcArea();
}
""",

"""
double
perimeter(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    const GA_Primitive         *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GA_Primitive *)gdp->getPrimitiveList().get(primOff);

    return prim->calcPerimeter();
}
""",

"""
void
reversePrimitive(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    GEO_Primitive               *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GEO_Primitive *)gdp->getPrimitiveList().get(primOff);

    return prim->reverse();
}
""",

"""
void
makeUnique(GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    GEO_Primitive               *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GEO_Primitive *)gdp->getPrimitiveList().get(primOff);

    gdp->uniquePrimitive(prim);
}
""",

"""
BoundingBox
boundingBox(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    const GEO_Primitive         *prim;

    UT_BoundingBox              bbox;

    BoundingBox                 bound;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GEO_Primitive *)gdp->getPrimitiveList().get(primOff);

    prim->getBBox(&bbox);

    bound.xmin = bbox.xmin();
    bound.ymin = bbox.ymin();
    bound.zmin = bbox.zmin();

    bound.xmax = bbox.xmax();
    bound.ymax = bbox.ymax();
    bound.zmax = bbox.zmax();

    return bound;
}
""",

"""
BoundingBox
primGroupBoundingBox(const GU_Detail *gdp, const char *group_name)
{

    const GA_PrimitiveGroup     *group;

    UT_BoundingBox              bbox;

    BoundingBox                 bound;

    // Find the primitive group.
    group = gdp->findPrimitiveGroup(group_name);

    gdp->getBBox(&bbox, group);

    bound.xmin = bbox.xmin();
    bound.ymin = bbox.ymin();
    bound.zmin = bbox.zmin();

    bound.xmax = bbox.xmax();
    bound.ymax = bbox.ymax();
    bound.zmax = bbox.zmax();

    return bound;
}
""",

"""
BoundingBox
pointGroupBoundingBox(const GU_Detail *gdp, const char *group_name)
{

    const GA_PointGroup         *group;

    UT_BoundingBox              bbox;

    BoundingBox                 bound;

    // Find the point group.
    group = gdp->findPointGroup(group_name);

    gdp->getPointBBox(&bbox, group);

    bound.xmin = bbox.xmin();
    bound.ymin = bbox.ymin();
    bound.zmin = bbox.zmin();

    bound.xmax = bbox.xmax();
    bound.ymax = bbox.ymax();
    bound.zmax = bbox.zmax();

    return bound;
}
""",

"""
bool
addNormalAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           n_gah;

    n_gah = gdp->addNormalAttribute(GA_ATTRIB_POINT);

    // Return true if the attribute was created.
    if (n_gah.isValid())
    {
        return true;
    }

    // False otherwise.
    return false;
}
""",

"""
bool
addVelocityAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           v_gah;

    v_gah = gdp->addVelocityAttribute(GA_ATTRIB_POINT);

    // Return true if the attribute was created.
    if (v_gah.isValid())
    {
        return true;
    }

    // False otherwise.
    return false;
}
""",

"""
bool
addDiffuseAttribute(GU_Detail *gdp, int mode)
{
    GA_RWAttributeRef           diff_gah;

    switch (mode)
    {
        case 0:
            diff_gah = gdp->addDiffuseAttribute(GA_ATTRIB_POINT);
            break;

        case 1:
            diff_gah = gdp->addDiffuseAttribute(GA_ATTRIB_PRIMITIVE);
            break;

        case 2:
            diff_gah = gdp->addDiffuseAttribute(GA_ATTRIB_VERTEX);
            break;

        default:
            break;
    }

    // Return true if the attribute was created.
    if (diff_gah.isValid())
    {
        return true;
    }

    // False otherwise.
    return false;
}
""",

"""
void
computePointNormals(GU_Detail *gdp)
{
    gdp->normal();
}
""",

"""
void
convexPolygons(GU_Detail *gdp, unsigned maxpts=3)
{
    gdp->convex(maxpts);
}
""",

"""
void
destroyEmptyGroups(GU_Detail *gdp, int mode)
{
    if (mode)
    {
        gdp->destroyEmptyGroups(GA_ATTRIB_PRIMITIVE);
    }
    else
    {
        gdp->destroyEmptyGroups(GA_ATTRIB_POINT);
    }
}
""",

"""
void
destroyUnusedPoints(GU_Detail *gdp, const char *group_name)
{
    GA_PointGroup               *group = 0;

    // If we passed in a valid group, try to find it.
    if (group_name)
    {
        group = gdp->findPointGroup(group_name);
    }

    gdp->destroyUnusedPoints(group);
}
""",

"""
void
consolidatePoints(GU_Detail *gdp, double distance, const char *group_name)
{
    GA_PointGroup               *group = 0;

    if (group_name)
    {
        group = gdp->findPointGroup(group_name);
    }

    gdp->fastConsolidatePoints(distance, group);
}
""",

"""
void
uniquePoints(GU_Detail *gdp, const char *group_name, int group_type)
{
    GA_ElementGroup             *group = 0;

    if (group_name)
    {
        if (group_type)
        {
            group = gdp->findPrimitiveGroup(group_name);
        }
        else
        {
            group = gdp->findPointGroup(group_name);
        }
    }

    gdp->uniquePoints(group);
}
""",

"""
void
toggleMembership(GU_Detail *gdp, const char *group_name,
                 int group_type, int elem_num)
{
    GA_ElementGroup             *group = 0;
    GA_Offset                   elem_offset;

    if (group_type)
    {
        group = gdp->findPrimitiveGroup(group_name);
        elem_offset = gdp->primitiveOffset(elem_num);
    }
    else
    {
        group = gdp->findPointGroup(group_name);
        elem_offset = gdp->pointOffset(elem_num);
    }

    group->toggleOffset(elem_offset);
}
""",

"""
void
setEntries(GU_Detail *gdp, const char *group_name, int group_type)
{
    GA_ElementGroup             *group = 0;

    if (group_type)
    {
        group = gdp->findPrimitiveGroup(group_name);
    }
    else
    {
        group = gdp->findPointGroup(group_name);
    }

    group->setEntries();

}
""",

"""
void
toggleEntries(GU_Detail *gdp, const char *group_name, int group_type)
{
    GA_ElementGroup             *group = 0;

    if (group_type)
    {
        group = gdp->findPrimitiveGroup(group_name);
    }
    else
    {
        group = gdp->findPointGroup(group_name);
    }

    group->toggleEntries();
}
""",

"""
void
copyGroup(GU_Detail *gdp,
          int group_type,
          const char *group_name,
          const char *new_group_name)
{
    GA_AttributeOwner           owner;
    const GA_ElementGroup       *group;
    GA_ElementGroup             *new_group;

    owner = group_type ? GA_ATTRIB_PRIMITIVE : GA_ATTRIB_POINT;

    // Find the current group.
    group = gdp->findElementGroup(owner, group_name);

    // Create the new group.
    new_group = gdp->createElementGroup(owner, new_group_name);

    // Copy the membership to the new group.
    new_group->copyMembership(*group);
}
""",

"""
bool
containsAny(const GU_Detail *gdp,
            const char *group_name,
            const char *other_group_name,
            int group_type)
{
    const GA_ElementGroup       *group;

    const GA_PrimitiveGroup     *prim_group;
    const GA_PointGroup         *point_group;

    GA_Range                    range;

    if (group_type)
    {
        group = gdp->findPrimitiveGroup(group_name);
        prim_group = gdp->findPrimitiveGroup(other_group_name);
        range = gdp->getPrimitiveRange(prim_group);
    }
    else
    {
        group = gdp->findPointGroup(group_name);
        point_group = gdp->findPointGroup(other_group_name);
        range = gdp->getPointRange(point_group);
    }

    return group->containsAny(range);
}
""",

"""
void
primToPointGroup(GU_Detail *gdp,
                      const char *group_name,
                      const char *new_group_name,
                      bool destroy)
{
    GA_PrimitiveGroup           *prim_group;
    GA_PointGroup               *point_group;

    GA_Range                    pr_range, pt_range;

    // Get the list of primitives.
    const GA_PrimitiveList &prim_list = gdp->getPrimitiveList();

    // The source group.
    prim_group = gdp->findPrimitiveGroup(group_name);

    // Create a new point group.
    point_group = gdp->newPointGroup(new_group_name);

    // Get the range of primitives in the source group.
    pr_range = GA_Range(*prim_group);

    for (GA_Iterator pr_it(pr_range); !pr_it.atEnd(); ++pr_it)
    {
        // Get the range of points referenced by the vertices of
        // the primitive.
        pt_range = prim_list.get(*pr_it)->getPointRange();
        // Add each point offset to the group.
        for (GA_Iterator pt_it(pt_range); !pt_it.atEnd(); ++pt_it)
        {
            point_group->addOffset(*pt_it);
        }
    }

    // Destroy the source group if necessary.
    if (destroy)
    {
        gdp->destroyPrimitiveGroup(prim_group);
    }
}
""",

"""
void
pointToPrimGroup(GU_Detail *gdp,
                      const char *group_name,
                      const char *new_group_name,
                      bool destroy)
{
    GA_PrimitiveGroup           *prim_group;
    GA_PointGroup               *point_group;

    GA_Range                    pr_range, pt_range;

    GA_OffsetArray              prims;
    GA_OffsetArray::const_iterator prims_it;

    // The source group.
    point_group = gdp->findPointGroup(group_name);

    // Create a new primitive group.
    prim_group = gdp->newPrimitiveGroup(new_group_name);

    // The range of points in the source group.
    pt_range = GA_Range(*point_group);

    for (GA_Iterator pt_it(pt_range); !pt_it.atEnd(); ++pt_it)
    {
        // Get an array of primitives that reference the point.
        gdp->getPrimitivesReferencingPoint(prims, *pt_it);

        // Add each primitive offset to the group.
        for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
        {
            prim_group->addOffset(*prims_it);
        }
    }

    // Destroy the source group if necessary.
    if (destroy)
    {
        gdp->destroyPointGroup(point_group);
    }
}
""",

"""
void
clip(GU_Detail *gdp, UT_Vector3D *normal, float dist)
{
    UT_Vector3 dir(*normal);

    GQ_Detail                   *gqd = new GQ_Detail(gdp);

    gqd->clip(dir, dist, 0);
    delete gqd;
}
""",

"""
bool
isInside(const UT_BoundingBoxD *bbox1, const UT_BoundingBoxD *bbox2)
{
    return bbox1->isInside(*bbox2);
}
""",

"""
bool
intersects(UT_BoundingBoxD *bbox1, const UT_BoundingBoxD *bbox2)
{
    return bbox1->intersects(*bbox2);
}
""",

"""
bool
computeIntersection(UT_BoundingBoxD *bbox1, const UT_BoundingBoxD *bbox2)
{
    return bbox1->computeIntersection(*bbox2);
}
""",

"""
void
expandBounds(UT_BoundingBoxD *bbox, float dltx, float dlty, float dltz)
{
    bbox->expandBounds(dltx, dlty, dltz);
}
""",

"""
void
addToMin(UT_BoundingBoxD *bbox, const UT_Vector3D *vec)
{
    bbox->addToMin(*vec);
}
""",

"""
void
addToMax(UT_BoundingBoxD *bbox, const UT_Vector3D *vec)
{
    bbox->addToMax(*vec);
}
""",

"""
double
boundingBoxArea(const UT_BoundingBoxD *bbox)
{
    return bbox->area();
}
""",

"""
double
boundingBoxVolume(const UT_BoundingBoxD *bbox)
{
    return bbox->volume();
}
""",

"""
bool
isParmDefault(OP_Node *node, const char *parm_name, int index)
{
    PRM_Parm &parm = node->getParm(parm_name);

    // If we have a specific index, check if that parm is at its default.
    if (index != -1)
    {
        return parm.isDefault(index);
    }

    // If not we check if the entire parm is at the default value.
    return parm.isDefault();
}
""",

"""
StringArray
getReferencingParms(OP_Node *node, const char *parm_name)
{
    std::vector<std::string>    result;

    PRM_Parm                    *parm_tuple;

    UT_PtrArray<PRM_Parm *>     parm_tuples;
    UT_IntArray                 component_indices;

    UT_String                   path, chan;

    // Get an array of parameter objects and their component indices
    // that reference the parameter.
    node->getParmsThatReference(parm_name, parm_tuples, component_indices);

    for (int i=0; i < parm_tuples.entries(); ++i)
    {
        parm_tuple = parm_tuples[i];
        parm_tuple->getParmOwner()->getFullPath(path);
        path += "/";

        parm_tuple->getTemplatePtr()->getChannelToken(chan,
                                                      component_indices[i]);
        path += chan;

        result.push_back(path.toStdString());
    }

    if (result.size() == 0)
    {
        result.push_back("");
    }

    return result;
}
""",

"""
void
disconnectAllInputs(OP_Node *node)
{
    node->disconnectAllInputs();
}
""",

"""
void
disconnectAllOutputs(OP_Node *node)
{
    node->disconnectAllOutputs();
}
""",

"""
const char *
inputLabel(OP_Node *node, int index)
{
    return node->inputLabel(index);
}
""",

"""
StringArray
messageNodes(const OP_Node *node)
{
    std::vector<std::string>    paths;

    OP_Network                  *network;
    OP_NodeList                 nodes;

    UT_String                   path;

    // Cast to a network.
    network = (OP_Network *)node;

    // Get any message nodes.  If there are none, add an emptry string to
    // the list of paths and return it.
    if (!network->getMessageSubNodes(nodes))
    {
        paths.push_back("");
        return paths;
    }

    // Add each message node path to the list.
    for (int i=0; i<nodes.entries(); ++i)
    {
        nodes[i]->getFullPath(path);
        paths.push_back(path.toStdString());
    }

    // Return the paths.
    return paths;
}
""",

"""
int
representativeNode(const OP_Node *node)
{
    OP_Network                  *network;

    network = (OP_Network *)node;

    return network->getRepresentativeNodeId(0, 0);
}
""",

"""
bool
isContainedBy(const OP_Node *node, const OP_Node *parent)
{
    return node->getIsContainedBy(parent);
}
""",

"""
bool
isEditable(const OP_Node *node)
{
    return node->getIsEditableAssetSubNode();
}
""",

"""
bool
isCompiled(const OP_Node *node)
{
    return node->isCompiled();
}
""",

"""
StringArray
getExistingOpReferences(OP_Node *node, bool recurse)
{
    std::vector<std::string>    result;

    UT_String                   path;

    OP_Node                     *ref_node;

    OP_NodeList                 refs;
    OP_NodeList::const_iterator depend_it;

    node->getExistingOpReferences(refs, recurse);

    for (depend_it=refs.begin(); !depend_it.atEnd(); ++depend_it)
    {
        ref_node = *depend_it;
        ref_node->getFullPath(path);

        result.push_back(path.toStdString());
    }

    if (result.size() == 0)
    {
        result.push_back("");
    }

    return result;
}
""",

"""
StringArray
getExistingOpDependents(OP_Node *node, bool recurse)
{
    std::vector<std::string>    result;

    UT_String                   path;

    OP_Node                     *dep_node;

    OP_NodeList                 deps;
    OP_NodeList::const_iterator depend_it;

    node->getExistingOpDependents(deps, recurse);

    for (depend_it=deps.begin(); !depend_it.atEnd(); ++depend_it)
    {
        dep_node = *depend_it;
        dep_node->getFullPath(path);

        result.push_back(path.toStdString());
    }

    if (result.size() == 0)
    {
        result.push_back("");
    }

    return result;
}
""",

"""
void
insertMultiParmItem(OP_Node *node, const char *parm_name, int idx)
{
    node->insertMultiParmItem(parm_name, idx);
}
""",

"""
void
removeMultiParmItem(OP_Node *node, const char *parm_name, int idx)
{
    node->removeMultiParmItem(parm_name, idx);
}
""",

"""
StringTuple
getMultiParmInstances(OP_Node *node, const char *parm_name)
{
    int                         items, instances;
    std::vector<StringArray>    blocks;

    PRM_Parm                    *parm;
    PRM_Parm &multiparm = node->getParm(parm_name);

    // The number of multi parm blocks.
    items = multiparm.getMultiParmNumItems();

    // The number of parms in each block.
    instances = multiparm.getMultiParmInstancesPerItem();

    for (int i=0; i < items; ++i)
    {
        std::vector<std::string>    result;

        for (int j=0; j < instances; ++j)
        {
            parm = multiparm.getMultiParm(i * instances + j);
            result.push_back(parm->getToken());
        }

        // If the block is empty, add an empty string.
        if (result.size() == 0)
        {
            result.push_back("");
        }

        blocks.push_back(result);
    }

    // If there are no entries, add an emptry block.
    if (blocks.size() == 0)
    {
        std::vector<std::string>    result;
        result.push_back("");
        blocks.push_back(result);
    }

    return blocks;
}
""",

"""
void
buildLookat(UT_DMatrix3 *mat,
            const UT_Vector3D *from,
            const UT_Vector3D *to,
            const UT_Vector3D *up)
{
    mat->lookat(*from, *to, *up);
}
""",

"""
void
getDual(const UT_Vector3D *vec, UT_DMatrix3 *mat)
{
    vec->getDual(*mat);
}
""",

"""const char *
getMetaSource(const char *filename)
{
    OP_OTLLibrary       *lib;

    int                 idx;

    UT_String           test;

    OP_OTLManager &manager = OPgetDirector()->getOTLManager();
    idx = manager.findLibrary(filename);

    lib = (idx >= 0) ? manager.getLibrary(idx): NULL;

    if (lib)
    {
        return lib->getMetaSource();
    }

    return "";
}
""",]
)

@addToModule(hou)
def expandRange(pattern):
    """Expand a string range into a tuple of values.

    Args:
        pattern : (str)
            A string containing values to expand.

    Returns:
        tuple
            A tuple of integers representing any ranges.

    Raises: N/A

    This function will do string range expansion.  Examples include
    '0-15', '0 4 10-100', '1-100:2', etc.  See Houdini's documentation
    about geometry groups for more information. Wildcards are not supported.

    """
    return tuple(_cpp_methods.expandRange(pattern))


@addToClass(hou.Geometry)
def isReadOnly(self):
    """Check if the geometry is read only.

    Returns:
        bool
            Returns True if the geometry is read only, otherwise False.

    Raises: N/A

    """
    # Get a GU Detail Handle for the geometry.
    handle = self._guDetailHandle()
    # Check if the handle is read only.
    result = handle.isReadOnly()
    # Destroy the handle.
    handle.destroy()

    return result


@addToClass(hou.Geometry)
def sortAlongAxis(self, geometry_type, axis):
    """Sort points or primitives based on increasing positions along an axis.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.
        axis : (int)
            The axis to sort along: (X=0, Y=1, Z=2).

    Returns: N/A

    Raises:
        ValueError
            This exception is raised if 'axis' is not 0, 1 or 2.
        OperationFailed
            This exception is raised if 'geometry_type' is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    """
    # Verify the axis.
    if axis not in range(3):
        raise ValueError("Invalid axis: {0}".format(axis))

    # Sort the points along an axis.
    if geometry_type == hou.geometryType.Points:
        _cpp_methods.sortAlongAxis(self, 0, axis)

    # Sort the primitives along an axis.
    elif geometry_type == hou.geometryType.Primitives:
        _cpp_methods.sortAlongAxis(self, 1, axis)

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )


@addToClass(hou.Geometry)
def sortByValues(self, geometry_type, values):
    """Sort points or primitives based on a list of corresponding values.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.
        values : (list)
            A list of numbers to sort by.

    Returns: N/A

    Raises:
        OperationFailed
            This exception is raised if 'geometry_type' is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    The list of values must be the same length as the number of geometry
    elements to be sourced.

    """
    if geometry_type == hou.geometryType.Points:
        # Check we have enough points.
        if len(values) != len(self.iterPoints()):
            raise hou.OperationFailed(
                "Length of values must equal the number of points."
            )

        # Construct a ctypes float array to pass the values.
        arr = _buildCFloatArray(values)

        _cpp_methods.sortByValues(self, 0, arr)

    elif geometry_type == hou.geometryType.Primitives:
        # Check we have enough primitives.
        if len(values) != len(self.iterPrims()):
            raise hou.OperationFailed(
                "Length of values must equal the number of prims."
            )

        # Construct a ctypes float array to pass the values.
        arr = _buildCFloatArray(values)

        _cpp_methods.sortByValues(self, 1, arr)

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )


@addToClass(hou.Geometry)
def sortRandomly(self, geometry_type, seed=0.0):
    """Sort points or primitives randomly.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.
        seed=0.0 : (float)
            The amount to shift each elements number.

    Returns: N/A

    Raises:
        TypeError
            This exception is raised if 'seed' is not a number.
        OperationFailed
            This exception is raised if 'geometry_type' is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    """
    if not isinstance(seed, (float, int)):
        raise TypeError(
            "Got '{0}', expected 'float'.".format(type(seed).__name__)
        )

    # Randomize the point order.
    if geometry_type == hou.geometryType.Points:
        _cpp_methods.sortListRandomly(self, 0, seed)

    # Randomize the primitive order.
    elif geometry_type == hou.geometryType.Primitives:
        _cpp_methods.sortListRandomly(self, 1, seed)

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )


@addToClass(hou.Geometry)
def shiftElements(self, geometry_type, offset=0):
    """Shift all point or primitives indices forward by an offset.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.
        offset=0 : (int)
            The amount to shift each elements number.

    Returns: N/A

    Raises:
        TypeError
            This exception is raised if 'offset' is not an integer.
        OperationFailed
            This exception is raised if 'geometry_type' is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    Each point or primitive number gets the offset added to it to get its new
    number.  If this exceeds the number of points or primitives, it wraps
    around.

    """
    if not isinstance(offset, int):
        raise TypeError(
            "Got '{0}', expected 'int'.".format(type(offset).__name__)
        )

    # Shift the point order.
    if geometry_type == hou.geometryType.Points:
        _cpp_methods.shiftList(self, 0, offset)

    # Shift the primitive order.
    elif geometry_type == hou.geometryType.Primitives:
        _cpp_methods.shiftList(self, 1, offset)

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )


@addToClass(hou.Geometry)
def reverseSort(self, geometry_type):
    """Reverse the ordering of the points or primitives.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.

    Returns: N/A

    Raises:
        OperationFailed
            This exception is raised if geometry_type is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    The highest numbered becomes the lowest numbered, and vice versa.

    """
    # Reverse the point order.
    if geometry_type == hou.geometryType.Points:
        _cpp_methods.reverseList(self, 0)

    # Reverse the primitive order.
    elif geometry_type == hou.geometryType.Primitives:
        _cpp_methods.reverseList(self, 1)

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )


@addToClass(hou.Geometry)
def sortByProximityToPosition(self, geometry_type, pos):
    """Sort elements by their proximity to a point.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.
        pos : (hou.Vector3)
            A location in space.

    Returns: N/A

    Raises:
        OperationFailed
            This exception is raised if geometry_type is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    The distance to the point in space is used as a priority. The points or
    primitives are then sorted so that the 0th entity is the one closest to
    that point.
    """
    # Sort the points.
    if geometry_type == hou.geometryType.Points:
        _cpp_methods.proximityToList(self, 0, pos)

    # Sort the primitives.
    elif geometry_type == hou.geometryType.Primitives:
        _cpp_methods.proximityToList(self, 1, pos)

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )


@addToClass(hou.Geometry)
def sortByVertexOrder(self):
    """Sorts points to match the order of the vertices on the primitives.

    Returns: N/A

    Raises: N/A

    If you have a curve whose point numbers do not increase along the curve,
    this will reorder the point numbers so they match the curve direction.

    """
    _cpp_methods.sortByVertexOrder(self)


@addToClass(hou.Geometry)
def sortByExpression(self, geometry_type, expression):
    """Sort points or primitives based on an expression for each element.

    Args:
        geometry_type : (hou.geometryType)
            The type of geometry elements to sort.
        expression : (str)
            An expression to evaluate for each point or primitive.

    Returns: N/A

    Raises:
        hou.GeometryPermissionError
            This exception is raised if the geometry is not writeable.
        OperationFailed
            This exception is raised if geometry_type is not one of
            (hou.geometryType.Points or hou.geometryType.Primitives).

    The specified expression is evaluated for each point or primitive. This
    determines the priority of that primitive, and the entities are reordered
    according to that priority. The point or primitive with the least evaluated
    expression value will be numbered 0 after the sort.

    """
    # Make sure the geometry is not read only.
    if self.isReadOnly():
        raise hou.GeometryPermissionError()

    values = []

    # Get the current cooking SOP node.  We need to do this as the geometry is
    # frozen and  has no reference to the SOP node it belongs to.
    sop_node = hou.pwd()

    if geometry_type == hou.geometryType.Points:
        # Iterate over each point.
        for point in self.points():
            # Get this point to be the current point.  This allows '$PT' to
            # work properly in the expression.
            sop_node.setCurPoint(point)
            # Add the evaluated expression value to the list.
            values.append(hou.hscriptExpression(expression))

    elif geometry_type == hou.geometryType.Primitives:
        # Iterate over each primitive.
        for prim in self.prims():
            # Get this point to be the current point.  This allows '$PR' to
            # work properly in the expression.
            sop_node.setCurPrim(prim)
            # Add the evaluated expression value to the list.
            values.append(hou.hscriptExpression(expression))

    else:
        raise hou.OperationFailed(
            "Geometry type must be points or primitives."
        )

    sortByValues(self, geometry_type, values)


@addToClass(hou.Geometry)
def createPoint(self, position=None):
    """Create a new point, optionally located at a position.

    Args:
        position=None : (hou.Vector3)
            The position to create the point at.  A value of None will
            create the point at the origin.

    Returns:
        hou.Point
            The newly created point.

    Raises: N/A

    """
    # If no position is specified, use the origin.
    if position is None:
        position = hou.Vector3()

    result = _cpp_methods.createPoint(self, position)

    return self.iterPoints()[result]


@addToClass(hou.Geometry)
def createPoints(self, count):
    """Create a specific number of new points.

    Args:
        count : (int)
            The number of new points to create.

    Returns:
        tuple
            A tuple of the hou.Point objects created.

    Raises:
        hou.OperationFailed
            Raise this exception if count is not greater than 0.

    """
    if count <= 0:
        raise hou.OperationFailed("Invalid number of points.")

    result = _cpp_methods.createPoints(self, count)

    return _getPointsFromList(self, result)


@addToClass(hou.Geometry)
def varmap(self):
    """Get the varmap as a dictionary.

    Returns:
        dict|None
            A dictionary representing the varmap attribute, if it exists.  If
            the attribute does not exist, returns None.

    Raises: N/A

    This function returns a dictionary representing the varmap attribute whose
    keys are the attribute names and values are the variable names.

    """
    # Try to find the detail attribute.
    varmap_attrib = self.findGlobalAttrib("varmap")

    # If it does not exists, return None.
    if varmap_attrib is None:
        return None

    # Get the value(s).
    values = self.attribValue(varmap_attrib)

    # If the value is a single string, convert it to a tuple.
    if isinstance(values, str):
        values = (values, )

    # The varmap dictionary.
    varmap_dict = {}

    for entry in values:
        # Split the value based on the mapping indicator.
        attrib_name, var = entry.split(" -> ")

        # Add the information to the dictionary.
        varmap_dict[attrib_name] = var

    return varmap_dict


@addToClass(hou.Geometry)
def setVarmap(self, varmap_dict):
    """Set the varmap based on the dictionary.

    Args:
        varmap_dict : (dict)
            A dictionary of attribute and variable names to set
            the varmap as.

    Returns: N/A

    Raises: N/A

    This function will create variable mappings between the keys and values of
    the dictionary.  If the attribute does not exist it will be created.

    """
    # Create varmap string mappings from the key/value pairs.
    strings = ["{0} -> {1}".format(attrib_name, var)
               for attrib_name, var in varmap_dict.iteritems()]

    # Construct a ctypes string array to pass the strings.
    arr = _buildCStringArray(strings)

    # Update the varmap.
    _cpp_methods.setVarmap(self, arr, len(strings))


@addToClass(hou.Geometry)
def addVariableName(self, attrib, var_name):
    """Add a variable mapping to the attribute in the varmap.

    Args:
        attrib : (hou.Attrib)
            The attribute to create a variable mapping for.
        var_name : (string)
            The variable name to map to the attribute.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.addVariableName(self, attrib.name(), var_name)


@addToClass(hou.Geometry)
def removeVariableName(self, var_name):
    """Remove a variable mapping from the varmap.

    Args:
        var_name : (string)
            The variable name to remove the mapping for.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.removeVariableName(self, var_name)


@addToClass(hou.Attrib, name="rename")
def renameAttribute(self, new_name):
    """Rename this attribute.

    Args:
        new_name : (string)
            The new attribute name.

    Returns:
        hou.Attrib|None
            Returns the newly renamed attribute if successful, otherwise
            None.

    Raises:
        hou.OperationFailed:
            Raises this exception if you try to destroy 'P'.

    """
    geometry = self.geometry()

    attrib_type = self.type()

    # Get the attribute type as an integer corresponding to the
    # GA_AttributeOwner enum.
    if attrib_type == hou.attribType.Vertex:
        owner = 0
    elif attrib_type == hou.attribType.Point:
        owner = 1
    elif attrib_type == hou.attribType.Prim:
        owner = 2
    else:
        owner = 3

    # Raise an exception when trying to modify 'P'.
    if attrib_type == hou.attribType.Point and self.name() == "P":
        raise hou.OperationFailed("Renaming 'P' is not permitted.")

    # Try to rename the attribute.
    success = _cpp_methods.renameAttribute(
        geometry,
        owner,
        self.name(),
        new_name
    )

    # That attribute was renamed.
    if success:
        # Return the new attribute.
        if attrib_type == hou.attribType.Vertex:
            return geometry.findVertexAttrib(new_name)
        elif attrib_type == hou.attribType.Point:
            return geometry.findPointAttrib(new_name)
        elif attrib_type == hou.attribType.Prim:
            return geometry.findPrimAttrib(new_name)
        else:
            return geometry.findGlobalAttrib(new_name)

    return None


@addToClass(hou.Geometry)
def findPrimByName(self, name_to_match, name_attribute="name", match_number=0):
    """Find a primitive with a matching name attribute value.

    Args:
        name_to_match : (string)
            The name attribute value to match.
        name_attribute="name" : (string)
            The attribute name to use.
        match_number=0 : (int)
            The match_numberth matching primitive to return.

    Returns:
        hou.Primitive|None
            A matching primitive, if found.  If no primitive is found, returns
            None.  None is also returned if match_number is greater than the
            number of matches found.

    Raises: N/A

    """
    # Try to find a primitive matching the name.
    result = _cpp_methods.findPrimitiveByName(
        self,
        name_to_match,
        name_attribute,
        match_number
    )

    # If the result is -1, no prims were found so return None.
    if result == -1:
        return None

    #  Return the primitive.
    return self.iterPrims()[result]


@addToClass(hou.Geometry)
def findAllPrimsByName(self, name_to_match, name_attribute="name"):
    """Find all primitives with a matching name attribute value.

    Args:
        name_to_match : (string)
            The name attribute value to match.
        name_attribute="name" : (string)
            The attribute name to use.

    Returns:
        tuple
            A tuple of hou.Prim objects whose attribute values match.

    Raises: N/A

    """
    # Try to find matching primitives.
    result = _cpp_methods.findAllPrimitivesByName(
        self,
        name_to_match,
        name_attribute
    )

    # Return a tuple of the matching primitives if any were found.
    if result:
        return _getPrimsFromList(self, result)

    # If none were found, return an empty tuple.
    return ()


@addToClass(hou.Point, name="copyAttributeValues")
def copyPointAttributeValues(self, source_point, attributes):
    """Copy attribute values from the source point to this point.

    Args:
        source_point : (hou.Point)
            The point to copy the attribute values from.
        attributes : (list)
            A list of hou.Attrib objects representing point attributes on the
            source geometry.

    Returns: N/A

    Raises: N/A

    If the attributes do not exist on the destination point they will be
    created.

    """
    # Get the source point's geometry.
    source_geometry = source_point.geometry()

    # Get the attribute names, ensuring we only use point attributes on the
    # source point's geometry.
    attrib_names = [
        attrib.name() for attrib in attributes
        if attrib.type() == hou.attribType.Point and
        attrib.geometry().sopNode() == source_geometry.sopNode()
    ]

    # Construct a ctypes string array to pass the strings.
    arr = _buildCStringArray(attrib_names)

    # Copy the values.
    _cpp_methods.copyPointAttributeValues(
        self.geometry(),
        self.number(),
        source_geometry,
        source_point.number(),
        arr,
        len(attrib_names)
    )


@addToClass(hou.Prim, name="copyAttributeValues")
def copyPrimAttributeValues(self, source_prim, attributes):
    """Copy attribute values from the source primitive to this primitive.

    Args:
        source_prim : (hou.Prim)
            The primitive to copy the attribute values from.
        attributes : (list)
            A list of hou.Attrib objects representing primitive attributes
            on the source geometry.

    Returns: N/A

    Raises: N/A

    If the attributes do not exist on the destination primitive they will be
    created.

    """
    # Get the source primitive's geometry.
    source_geometry = source_prim.geometry()

    # Get the attribute names, ensuring we only use primitive attributes on the
    # source primitive's geometry.
    attrib_names = [
        attrib.name() for attrib in attributes
        if attrib.type() == hou.attribType.Prim and
        attrib.geometry().sopNode() == source_geometry.sopNode()
    ]

    # Construct a ctypes string array to pass the strings.
    arr = _buildCStringArray(attrib_names)

    # Copy the values.
    _cpp_methods.copyPrimAttributeValues(
        self.geometry(),
        self.number(),
        source_geometry,
        source_prim.number(),
        arr,
        len(attrib_names)
    )


@addToClass(hou.Prim)
def pointAdjacentPolygons(self):
    """Get all prims that are adjacent to this prim through a point.

    Returns:
        tuple
            A tuple of hou.Prim objects.

    Raises: N/A

    """
    # Get the geometry this primitive belongs to.
    geometry = self.geometry()

    # Get a list of prim numbers that are point adjacent this prim.
    result = _cpp_methods.pointAdjacentPolygons(geometry, self.number())

    return _getPrimsFromList(geometry, result)


@addToClass(hou.Prim)
def edgeAdjacentPolygons(self):
    """Get all prims that are adjacent to this prim through an edge.

    Returns:
        tuple
            A tuple of hou.Prim objects.

    Raises: N/A

    """
    # Get the geometry this primitive belongs to.
    geometry = self.geometry()

    # Get a list of prim numbers that are edge adjacent this prim.
    result = _cpp_methods.edgeAdjacentPolygons(geometry, self.number())

    return _getPrimsFromList(geometry, result)


@addToClass(hou.Point)
def connectedPrims(self):
    """Get all primitives that reference this point.

    Returns:
        tuple
            A tuple of hou.Prim objects that reference the point.

    Raises: N/A

    """
    # Get the geometry the point belongs to.
    geometry = self.geometry()

    # Get a list of primitive numbers that reference the point.
    result = _cpp_methods.connectedPrims(geometry, self.number())

    return _getPrimsFromList(geometry, result)


@addToClass(hou.Point)
def connectedPoints(self):
    """Get all points that share an edge with this point.

    Returns:
        tuple
            A tuple of hou.Point objects that share an edge with
            the point.

    Raises: N/A

    """
    # Get the geometry the point belongs to.
    geometry = self.geometry()

    # Get a list of point numbers that are connected to the point.
    result = _cpp_methods.connectedPoints(geometry, self.number())

    # Glob for the points and return them.
    return _getPointsFromList(self, result)


@addToClass(hou.Point)
def referencingVertices(self):
    """Get all the vertices referencing this point.

    Returns:
        tuple
            A tuple of hou.Vertex objects that reference the point.

    Raises: N/A

    """
    # Get the geometry the point belongs to.
    geometry = self.geometry()

    # Get an object containing primitive and vertex index information.
    result = _cpp_methods.referencingVertices(geometry, self.number())

    # Construct a list of vertex strings.  Each element has the format:
    # {prim_num}v{vertex_index}.
    vertex_strings = ["{0}v{1}".format(prim, idx)
                      for prim, idx in zip(result.prims, result.indices)]

    # Glob for the vertices and return them.
    return geometry.globVertices(' '.join(vertex_strings))


@addToClass(hou.Geometry)
def pointStringAttribValues(self, name):
    """Return a tuple of strings containing one attribute's values for all the
    points.

    Args:
        name : (string)
            The name of the point attribute.

    Returns:
        tuple
            A tuple of strings representing the attribute values for
            each point.

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute name is invalid or the
            attribute is not a string attribute.

    """
    attrib = self.findPointAttrib(name)

    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    return _cpp_methods.pointStringAttribValues(self, name)


@addToClass(hou.Geometry)
def setPointStringAttribValues(self, name, values):
    """Set the string attribute values for all points.

    Args:
        name : (string)
            The name of the point attribute.
        values : (tuple)
            A tuple of strings representing the attribute values for each
            point.

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute name is invalid, the
            attribute is not a string, or the array of values is not the
            correct size.

    """
    attrib = self.findPointAttrib(name)

    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    if len(values) != len(self.iterPoints()):
        raise hou.OperationFailed("Incorrect attribute value sequence size.")

    # Construct a ctypes string array to pass the strings.
    arr = _buildCStringArray(values)

    return _cpp_methods.setPointStringAttribValues(
        self,
        name,
        arr,
        len(values)
    )


@addToClass(hou.Geometry)
def setSharedPointStringAttrib(self, attribute, value, group=None):
    """Set a string attribute value for points.

    Args:
        attribute : (hou.Attrib)
            The string attribute to set.
        value : (string)
            The attribute value to set.
        group=None (hou.PointGroup)
            An optional point group to specify which points to set.

    Returns: N/A

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute is invalid.

    If group is None, all points will have receive the value.  If a group is
    passed, only the points in the group will be set.

    """
    # If the group is valid, use that group's name.
    if group:
        group_name = group.name()
    # If not, pass an empty string to signify no group.
    else:
        group_name = ""

    result = _cpp_methods.setSharedPointStringAttrib(
        self,
        attribute.name(),
        value,
        group_name
    )

    # Check the result for errors.
    if result == 1:
        raise hou.OperationFailed("Invalid attribute.")


@addToClass(hou.Geometry)
def primStringAttribValues(self, name):
    """Return a tuple of strings containing one attribute's values for all the
    primitives.

    Args:
        name : (string)
            The name of the primitive attribute.

    Returns:
        tuple
            A tuple of strings representing the attribute values for each
            primitive.

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute name is invalid or the
            attribute is not a string.

    """
    attrib = self.findPrimAttrib(name)

    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    return _cpp_methods.primStringAttribValues(self, name)


@addToClass(hou.Geometry)
def setPrimStringAttribValues(self, name, values):
    """Set the string attribute values for all primitives.

    Args:
        name : (string)
            The name of the primitive attribute.
        values : (tuple)
            A tuple of strings representing the attribute values for each
            primitive.

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute name is invalid, the
            attribute is not a string, or the array of values is not the
            correct size.

    """
    attrib = self.findPrimAttrib(name)

    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    if len(values) != len(self.iterPrims()):
        raise hou.OperationFailed("Incorrect attribute value sequence size.")

    # Construct a ctypes string array to pass the strings.
    arr = _buildCStringArray(values)

    return _cpp_methods.setPrimStringAttribValues(
        self,
        name,
        arr,
        len(values)
    )


@addToClass(hou.Geometry)
def setSharedPrimStringAttrib(self, attribute, value, group=None):
    """Set a string attribute value for primitives.

    Args:
        attribute : (hou.Attrib)
            The string attribute to set.
        value : (string)
            The attribute value to set.
        group=None : (hou.PrimGroup)
            An optional primitive group to specify which primitives
            to set.

    Returns: N/A

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute is invalid.

    If group is None, all primitives will have receive the value.  If a group
    is passed, only the primitives in the group will be set.

    """
    # If the group is valid, use that group's name.
    if group:
        group_name = group.name()
    # If not, pass an empty string to signify no group.
    else:
        group_name = ""

    result = _cpp_methods.setSharedPrimStringAttrib(
        self,
        attribute.name(),
        value,
        group_name
    )

    # Check the result for errors.
    if result == 1:
        raise hou.OperationFailed("Invalid attribute.")


@addToClass(hou.Face)
def hasEdge(self, point1, point2):
    """Test if this face has an edge between two points.

    Args:
        point1 : (hou.Point)
            An edge point.
        point2 : (hou.Point)
            An edge point.

    Returns:
        bool
            Returns True if an edge exists, otherwise False.

    Raises: N/A

    """
    # Test for the edge.
    return _cpp_methods.hasEdge(
        self.geometry(),
        self.number(),
        point1.number(),
        point2.number()
    )


@addToClass(hou.Face)
def insertVertex(self, point, index):
    """Insert a vertex on the point into this face at a specific index.

    Args:
        point : (hou.Point)
            The point the vertex will be attached to.
        index : (int)
            The index of the vertex to insert.

    Returns: N/A

    Raises: N/A

    """
    # Insert the vertex.
    _cpp_methods.insertVertex(
        self.geometry(),
        self.number(),
        point.number(),
        index
    )


@addToClass(hou.Face)
def deleteVertex(self, index):
    """Delete the vertex at the specified index.

    Args:
        index : (int)
            The index of the vertex to delete.

    Returns: N/A

    Raises: N/A

    """
    # Delete teh vertex.
    _cpp_methods.deleteVertex(self.geometry(), self.number(), index)


@addToClass(hou.Face)
def setPoint(self, index, point):
    """Set the vertex, at the specified index, to be attached to the point.

    Args:
        index : (int)
            The index of the vertex to modify.
        point : (hou.Point)
            The point to attach the vertex to.

    Returns: N/A

    Raises: N/A

    """
    # Delete teh vertex.
    _cpp_methods.setPoint(
        self.geometry(),
        self.number(),
        index,
        point.number()
    )


@addToClass(hou.Prim)
def baryCenter(self):
    """Get the barycenter of this primitive.

    Returns:
        hou.Vector3
            The barycenter of the primitive.

    Raises: N/A

    """
    # Get the Position3D object representing the barycenter.
    pos = _cpp_methods.baryCenter(self.geometry(), self.number())

    # Construct a vector and return it.
    return hou.Vector3(pos.x, pos.y, pos.z)


@addToClass(hou.Prim, name="area")
def primitiveArea(self):
    """Get the area of this primitive.

    Returns:
        float
            The area of the primitive.

    Raises: N/A

    """
    # Calculate and return the area.
    return _cpp_methods.primitiveArea(self.geometry(), self.number())


@addToClass(hou.Prim)
def perimeter(self):
    """Get the perimeter of this primitive.

    Returns:
        float
            The perimeter of the primitive.

    Raises: N/A

    """
    # Calculate and return the perimeter.
    return _cpp_methods.perimeter(self.geometry(), self.number())


@addToClass(hou.Prim, name="reverse")
def reversePrim(self):
    """Reverse the vertex order of this primitive.

    Returns: N/A

    Raises: N/A

    """
    return _cpp_methods.reversePrimitive(self.geometry(), self.number())


@addToClass(hou.Prim)
def makeUnique(self):
    """Unique all the points that are in this primitive.

    Returns: N/A

    Raises: N/A

    This function will unique all the points even if they are referenced by
    other primitives.

    """
    return _cpp_methods.makeUnique(self.geometry(), self.number())


@addToClass(hou.Prim, name="boundingBox")
def primBoundingBox(self):
    """Get the bounding box of this primitive.

    Returns:
        hou.BoundingBox
            The bounding box of the primitive.

    Raises: N/A

    """
    # Calculate the bounds for the primitive.
    bounds = _cpp_methods.boundingBox(self.geometry(), self.number())

    # Convert the bounds to a hou.BoundingBox and return it.
    return _buildBoundingBox(bounds)


@addToClass(hou.Geometry, name="addPointNormals")
def addPointNormalAttribute(self):
    """Add point normals to the geometry.

    Returns:
        hou.Attrib
            Returns the newly created point attribute.

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute was not created.

    """
    result = _cpp_methods.addNormalAttribute(self)

    if result:
        return self.findPointAttrib("N")

    raise hou.OperationFailed("Could not add normal attribute.")


@addToClass(hou.Geometry, name="addPointVelocity")
def addPointVelocityAttribute(self):
    """Add point velocity to the geometry.

    Returns:
        hou.Attrib
            Returns the newly created point attribute.

    Raises:
        hou.OperationFailed
            Raise this exception if the attribute was not created.

    """
    result = _cpp_methods.addVelocityAttribute(self)

    if result:
        return self.findPointAttrib("v")

    raise hou.OperationFailed("Could not add velocity attribute.")


@addToClass(hou.Geometry)
def addColorAttribute(self, attrib_type):
    """Add a color (Cd) attribute to the geometry.

    Args:
        attrib_type : (hou.attribType)
            A hou.attribType value to specify if the attribute should be a
            point, primitive or vertex attribute.

    Returns:
        hou.Attrib
            Returns the newly created point attribute.

    Raises:
        hou.TypeError
            Raise this exception if attribute_type is not a valid type.
        hou.OperationFailed
            Raise this exception if the attribute was not created.

    Point, primitive and vertex colors are supported.

    """
    # Try to add a point Cd attribute.
    if attrib_type == hou.attribType.Point:
        result = _cpp_methods.addDiffuseAttribute(self, 0)

        if result:
            return self.findPointAttrib("Cd")

    # Try to add a primitive Cd attribute.
    elif attrib_type == hou.attribType.Prim:
        result = _cpp_methods.addDiffuseAttribute(self, 1)

        if result:
            return self.findPrimAttrib("Cd")

    # Try to add a vertex Cd attribute.
    elif attrib_type == hou.attribType.Vertex:
        result = _cpp_methods.addDiffuseAttribute(self, 2)

        if result:
            return self.findVertexAttrib("Cd")

    # The type didn't match any of the valid ones so we should thrown an
    # exception.
    else:
        raise hou.TypeError("Invalid attribute type.")

    # We didn't create an attribute, so throw an exception.
    raise hou.OperationFailed("Could not add Cd attribute.")


@addToClass(hou.Geometry)
def computePointNormals(self):
    """Computes the point normals for the geometry.

    Returns: N/A

    Raises: N/A

    This is equivalent to using a Point sop, selecting 'Add Normal' and
    leaving the default values.  It will add the 'N' attribute if it does not
    exist.

    """
    _cpp_methods.computePointNormals(self)


@addToClass(hou.Geometry)
def convex(self, max_points=3):
    """Convex the geometry into polygons with a certain number of points.

    Args:
        max_points : (int)
            The maximum number of points for each polygon.

    Returns: N/A

    Raises: N/A

    This operation is similar to using the Divide SOP and setting the 'Maximum
    Edges'.

    """
    _cpp_methods.convexPolygons(self, max_points)


@addToClass(hou.Geometry)
def clip(self, normal, dist):
    """Clip this geometry along a plane.

    Args:
        normal : (hou.Vector3)
            The normal of the plane to clip with.
        dist : (float)
            The distance along the normal to clip at.

    Returns: N/A

    """
    _cpp_methods.clip(self, normal.normalized(), dist)


@addToClass(hou.Geometry)
def destroyEmptyPointGroups(self):
    """Remove any empty point groups.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.destroyEmptyGroups(self, 0)


@addToClass(hou.Geometry)
def destroyEmptyPrimGroups(self):
    """Remove any empty primitive groups.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.destroyEmptyGroups(self, 1)


@addToClass(hou.Geometry)
def destroyUnusedPoints(self, group=None):
    """Remove any unused points.

    Args:
        group=None : (hou.PointGroup)
            An optional point group to restrict the removal.

    Returns: N/A

    Raises: N/A

    If group is not None, only unused points within the group are removed.

    """
    if group is not None:
        _cpp_methods.destroyUnusedPoints(self, group.name())
    else:
        _cpp_methods.destroyUnusedPoints(self, 0)


@addToClass(hou.Geometry)
def consolidatePoints(self, distance=0.001, group=None):
    """Consolidate points within a specified distance.

    Args:
        distance=0.001 : (float)
            The max distance to consolidate by.
        group=None : (hou.PointGroup)
            An optional point group to restrict the consolidation.

    Returns: N/A

    Raises: N/A

    If group is not None, only points in that group are consolidated.

    """
    if group is not None:
        _cpp_methods.consolidatePoints(self, distance, group.name())
    else:
        _cpp_methods.consolidatePoints(self, distance, 0)


@addToClass(hou.Geometry)
def uniquePoints(self, group=None):
    """Unique all points in the geometry.

    Args:
        group=None : (hou.PointGroup|hou.PrimGroup)
            An optional group to restrict the uniqueing to.

    Returns: N/A

    Raises: N/A

    If a point group is specified, only points in that group are uniqued.  If
    a primitive group is specified, only those primitives will have their
    points uniqued.

    """
    if group is not None:
        # Check the group type.
        if isinstance(group, hou.PrimGroup):
            group_type = 1
        # hou.PointGroup
        else:
            group_type = 0

        _cpp_methods.uniquePoints(self, group.name(), group_type)

    else:
        _cpp_methods.uniquePoints(self, 0, 0)


@addToClass(hou.PointGroup, hou.PrimGroup, name="boundingBox")
def groupBoundingBox(self):
    """Get the bounding box of this group.

    Returns:
        hou.BoundingBox
            The bounding box of this group.

    Raises: N/A

    """
    # Calculate the bounds for the group.
    if isinstance(self, hou.PrimGroup):
        bounds = _cpp_methods.primGroupBoundingBox(
            self.geometry(),
            self.name()
        )
    # Point group.
    else:
        bounds = _cpp_methods.pointGroupBoundingBox(
            self.geometry(),
            self.name()
        )

    # Convert the bounds to a hou.BoundingBox and return it.
    return _buildBoundingBox(bounds)


@addToClass(hou.PointGroup, name="toggle")
def togglePoint(self, point):
    """Toggle group membership for a point.

    Args:
        point : (hou.Point)
            The point whose membership to toggle.

    Returns: N/A

    Raises: N/A

    If the point is a part of the group, it will be removed.  If it isn't, it
    will be added.

    """
    geometry = self.geometry()

    _cpp_methods.toggleMembership(geometry, self.name(), 0, point.number())


@addToClass(hou.PrimGroup, name="toggle")
def togglePrim(self, prim):
    """Toggle group membership for a primitive.

    Args:
        prim : (hou.Prim)
            The primitive whose membership to toggle.

    Returns: N/A

    Raises: N/A

    If the primitive is a part of the group, it will be removed.  If it isnt,
    it will be added.

    """
    geometry = self.geometry()

    _cpp_methods.toggleMembership(geometry, self.name(), 1, prim.number())


@addToClass(hou.PointGroup, hou.PrimGroup)
def toggleEntries(self):
    """Toggle group membership for all elements in the group.

    Returns: N/A

    Raises: N/A

    All elements not in the group will be added to it and all that were in it
    will be removed.

    """
    geometry = self.geometry()

    if isinstance(self, hou.PrimGroup):
        group_type = 1
    # hou.PointGroup
    else:
        group_type = 0

    _cpp_methods.toggleEntries(geometry, self.name(), group_type)


@addToClass(hou.PointGroup, hou.PrimGroup, name="copy")
def copyGroup(self, new_group_name):
    """Create a group under the new name with the same membership.

    Args:
        new_group_name : (string)
            The new group name.

    Returns: N/A

    Raises:
        hou.OperationFailed
            Raise this exception if the new group name is the same as the
            source group name, or a group with the new name already exists.

    """
    geometry = self.geometry()

    # Ensure the new group doesn't have the same name.
    if new_group_name == self.name():
        raise hou.OperationFailed("Cannot copy to group with same name.")

    # A group under the new name already exists.
    new_group_exists = False

    if isinstance(self, hou.PrimGroup):
        group_type = 1
        # Found a group with the new name so set the flag to True.
        if geometry.findPrimGroup(new_group_name):
            new_group_exists = True
    # hou.PointGroup
    else:
        group_type = 0
        # Found a group with the new name so set the flag to True.
        if geometry.findPointGroup(new_group_name):
            new_group_exists = True

    # If a group with the new name already exists, raise an exception.
    if new_group_exists:
        raise hou.OperationFailed("A group with that name already exists.")

    # Copy the group.
    _cpp_methods.copyGroup(geometry, group_type, self.name(), new_group_name)


@addToClass(hou.PointGroup, name="containsAny")
def pointGroupContainsAny(self, group):
    """Returns whether or not any points in the group are in this group.

    Args:
        group : (hou.PointGroup)
            A point group which may have one or more points in
            this group.

    Returns:
        bool
            Returns True if the group has one or more points that are in this
            group, otherwise False.

    Raises: N/A

    """
    geometry = self.geometry()

    return _cpp_methods.containsAny(geometry, self.name(), group.name(), 0)


@addToClass(hou.PrimGroup, name="containsAny")
def primGroupContainsAny(self, group):
    """Returns whether or not any prims in the group are in this group.

    Args:
        group : (hou.PrimGroup)
            A prim group which may have one or more prims in
            this group.

    Returns:
        bool
            Returns True if the group has one or more primitives that are in
            this group, otherwise False.

    Raises: N/A

    """
    geometry = self.geometry()

    return _cpp_methods.containsAny(geometry, self.name(), group.name(), 1)


@addToClass(hou.PrimGroup)
def convertToPointGroup(self, new_group_name=None, destroy=True):
    """Create a new hou.Point group from this primitive group.

    Args:
        new_group_name=None : (string)
            The name of the new point group.  If None, the point group
            will receive the same name as the source group.
        destroy=True : (bool)
            Destroy the source primitive group.

    Returns:
        hou.PointGroup
            The newly created point group.

    Raises:
        hou.OperationFailed
            This exception is raised if there is already a point group
            with the specified name.

    The group will contain all the points referenced by all the vertices of the
    primitives in the group.

    """
    geometry = self.geometry()

    # If a new name isn't specified, use the current group name.
    if new_group_name is None:
        new_group_name = self.name()

    # If the group already exists, raise an exception.
    if geometry.findPointGroup(new_group_name):
        raise hou.OperationFailed("Group already exists.")

    # Convert the group.
    _cpp_methods.primToPointGroup(
        geometry,
        self.name(),
        new_group_name,
        destroy
    )

    # Return the new group.
    return geometry.findPointGroup(new_group_name)


@addToClass(hou.PointGroup)
def convertToPrimGroup(self, new_group_name=None, destroy=True):
    """Create a new hou.Prim group from this point group.

    Args:
        new_group_name=None : (string)
            The name of the new prim group.  If None, the prim group will
            receive the same name as the source group.
        destroy=True : (bool)
            Destroy the source point group.

    Returns:
        hou.PrimGroup
            The newly created prim group.

    Raises:
        hou.OperationFailed
            This exception is raised if there is already a prim group with the
            specified name.

    The group will contain all the primitives which have vertices referencing
    any of the points in the group.

    """
    geometry = self.geometry()

    # If a new name isn't specified, use the current group name.
    if new_group_name is None:
        new_group_name = self.name()

    # If the group already exists, raise an exception.
    if geometry.findPrimGroup(new_group_name):
        raise hou.OperationFailed("Group already exists.")

    # Convert the group.
    _cpp_methods.pointToPrimGroup(
        geometry,
        self.name(),
        new_group_name,
        destroy
    )

    # Return the new group.
    return geometry.findPrimGroup(new_group_name)


@addToClass(hou.BoundingBox)
def isInside(self, bbox):
    """Determine if this bounding box is totally enclosed by another box.

    Args:
        bbox : (hou.BoundingBox)
            A bounding box that might enclose this box.

    Returns:
        bool
            Returns True if the bounding box encloses this box, otherwise
            False.

    Raises: N/A

    """
    return _cpp_methods.isInside(self, bbox)


@addToClass(hou.BoundingBox)
def intersects(self, bbox):
    """Determine if the bounding boxes intersect.

    Args:
        bbox : (hou.BoundingBox)
            A bounding box to test intersection with.

    Returns:
        bool
            Returns True if the two bounding boxes intersect, otherwise False.

    Raises: N/A

    """
    return _cpp_methods.intersects(self, bbox)


@addToClass(hou.BoundingBox)
def computeIntersection(self, bbox):
    """Compute the intersection of two bounding boxes.

    Args:
        bbox : (hou.BoundingBox):
            A bounding box that is intersecting with this box.

    Returns:
        bool
            Returns True if the two bounding boxes intersect, otherwise False.

    Raises: N/A

    This function changes the bounds of this box to be those of the
    intersection of this box and the supplied box.

    """
    return _cpp_methods.computeIntersection(self, bbox)


@addToClass(hou.BoundingBox)
def expandBounds(self, dltx, dlty, dltz):
    """Expand the min and max bounds in each direction by the axis delta.

    Args:
        dltx : (float)
            The amount to expand each X axis bounds.
        dlty : (float)
            The amount to expand each Y axis bounds.
        dltz : (float)
            The amount to expand each Z axis bounds.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.expandBounds(self, dltx, dlty, dltz)


@addToClass(hou.BoundingBox)
def addToMin(self, vec):
    """Add values to the minimum bounds of this bounding box.

    Args:
        vec : (hou.Vector3)
            The amount to expand the minimum bound values.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.addToClassMin(self, vec)


@addToClass(hou.BoundingBox)
def addToMax(self, vec):
    """Add values to the maximum bounds of this bounding box.

    Args:
        vec : (hou.Vector3)
            The amount to expand the maximum bound values.

    Returns: N/A

    Raises: N/A

    """
    _cpp_methods.addToClassMax(self, vec)


@addToClass(hou.BoundingBox, name="area")
def boundingBoxArea(self):
    """Calculate the area of this bounding box.

    Returns:
        float
            The area of the surface of the bounding box.

    Raises: N/A

    """
    return _cpp_methods.boundingBoxArea(self)


@addToClass(hou.BoundingBox, name="volume")
def boundingBoxVolume(self):
    """Calculate the volume of this bounding box.

    Returns:
        float
            The volume of the bounding box.

    Raises: N/A

    """
    return _cpp_methods.boundingBoxVolume(self)


@addToClass(hou.Parm, name="isDefault")
def isParmDefault(self):
    """Check if this parameter is at its default value.

    Returns:
        bool
            Returns if the parameter is at its default value.

    Raises: N/A

    """
    # Get the node the parameter belongs to.
    node = self.node()

    # Get the index of the parameter.
    index = self.componentIndex()

    # Pass in the tuple name since we have to access the actual parm index.
    return _cpp_methods.isParmDefault(node, self.tuple().name(), index)


@addToClass(hou.ParmTuple, name="isDefault")
def isParmTupleDefault(self):
    """Check if this parameter tuple is at its default values.

    Returns:
        bool
            Returns if the parameter tuple is at its default values.

    Raises: N/A

    """
    # Get the node the parm tuple belongs to.
    node = self.node()

    # Pass in an index of -1 to say we care about the entire parameter, not
    # just a specific index.
    return _cpp_methods.isParmDefault(node, self.name(), -1)


@addToClass(hou.Parm)
def getReferencingParms(self):
    """Returns a tuple of parameters that reference this parameter.

    Returns:
        tuple
            A tuple of referencing hou.Parm objects.

    Raises: N/A

    """
    # Get the node.
    node = self.node()

    # Get any paths to referencing parms.
    result = _cpp_methods.getReferencingParms(node, self.name())

    # Create a tuple of parms.
    return tuple([hou.parm(parm_path) for parm_path in result if parm_path])


@addToClass(hou.Parm, hou.ParmTuple)
def isMultiParm(self):
    """Check if this parameter is a multiparm.

    Returns:
        bool
            Returns True if the parm is a multiparm, otherwise False.

    Raises: N/A

    """
    # Get the parameter template for the parm/tuple.
    parm_template = self.parmTemplate()

    # Make sure the parm is a folder parm.
    if isinstance(parm_template, hou.FolderParmTemplate):
        # Get the folder type.
        folder_type = parm_template.folderType()

        # A tuple of folder types that are multiparms.
        multi_types = (
            hou.folderType.MultiparmBlock,
            hou.folderType.ScrollingMultiparmBlock,
            hou.folderType.TabbedMultiparmBlock
        )

        # If the folder type is in the list return True.
        if folder_type in multi_types:
            return True

    return False


@addToClass(hou.Parm, hou.ParmTuple)
def insertMultiParmItem(self, index):
    """Insert a multiparm item at the specified index.

    Args:
        index : (int)
            The index for the new item.

    Returns: N/A

    Raises:
        hou.OperationFailed
            This exception is raised if the parameter is not a
            multiparm.

    This is the equivalent of hitting the Insert Before button (+) on a
    multiparm to insert a new block at that location.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    _cpp_methods.insertMultiParmItem(node, self.name(), index)


@addToClass(hou.Parm, hou.ParmTuple)
def removeMultiParmItem(self, index):
    """Remove a multiparm item at the specified index.

    Args:
        index : (int)
            The index to remove.

    Returns: N/A

    Raises:
        hou.OperationFailed
            This exception is raised if the parameter is not a
            multiparm.

    This is the equivalent of hitting the Remove button (x) on a multiparm
    to remove a block.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    _cpp_methods.removeMultiParmItem(node, self.name(), index)


@addToClass(hou.Parm, hou.ParmTuple)
def getMultiParmInstances(self):
    """Return all the parameters in this multiparm block.

    Returns:
        tuple
            A tuple of tuples representing the parameters of each multiparm
            instance.

    Raises:
        hou.OperationFailed
            This exception is raised if the parameter is not a multiparm.

    The parameters are returned as a tuple of parameters based on each
    instance.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    # Get the multiparm parameter names.
    result = _cpp_methods.getMultiParmInstances(node, self.name())

    multi_parms = []

    # Iterate over each multiparm instance.
    for block in result:
        # Build a list of parameters in the instance.
        parms = [node.parm(parm_name) for parm_name in block if parm_name]
        multi_parms.append(tuple(parms))

    return tuple(multi_parms)


@addToClass(hou.Parm, hou.ParmTuple)
def getMultiParmInstanceValues(self):
    """Return all the parameter values in this multiparm block.

    Returns:
        tuple
            A tuple of tuples representing the values of each multiparm
            instance.

    Raises:
        hou.OperationFailed
            This exception is raised if the parameter is not a multiparm.

    The values are returned as a tuple of values based on each instance.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    # Get the multiparm parameters.
    parms = getMultiParmInstances(self)

    all_values = []

    # Iterate over each multiparm instance.
    for block in parms:
        # Build a list of parameter values.
        values = [parm.eval() for parm in block]
        all_values.append(tuple(values))

    return tuple(all_values)


@addToClass(hou.Node)
def disconnectAllInputs(self):
    """Disconnect all of this node's inputs.

    Returns: N/A

    Raises: N/A

    """
    return _cpp_methods.disconnectAllInputs(self)


@addToClass(hou.Node)
def disconnectAllOutputs(self):
    """Disconnect all of this node's outputs.

    Returns: N/A

    Raises: N/A

    """
    return _cpp_methods.disconnectAllOutputs(self)


@addToClass(hou.Node)
def inputLabel(self, index):
    """Returns the input label for this node at the specified index.

    Args:
        index : (int)
            The input index.

    Returns:
        string
            The label for the input.

    Raises:
        hou.IndexError
            Raise this exception if the index is out of range.

    """
    if index not in range(0, self.nodeType.maxNumInputs()):
        raise IndexError("Index out of range.")

    return _cpp_methods.inputLabel(self, index)


@addToClass(hou.Node)
def messageNodes(self):
    """Get any of this node's message nodes.

    Returns:
        tuple|None
            Returns a tuple of hou.Nodes if there are any message nodes,
            otherwise None.

    Raises: N/A

    """
    # Get any message node paths.
    result = _cpp_methods.messageNodes(self)

    # Convert them to hou.Nodes.
    return _getNodesFromPaths(result)


@addToClass(hou.Node)
def representativeNode(self):
    """Get the representative node of this node, if any.

    Returns:
        hou.Node|None
            Returns the representative hou.Node if one exists, otherwise None.

    Raises: N/A

    """
    session_id = _cpp_methods.representativeNode(self)

    return hou.nodeBySessionId(session_id)


@addToClass(hou.Node)
def isContainedBy(self, node):
    """Test if this node is a contained within the node.

    Args:
        node : (hou.Node)
            A node that may contain this node.

    Returns:
        bool
            Returns True if this node is contained in the node, otherwise
            False.

    Raises: N/A

    """
    return _cpp_methods.isContainedBy(self, node)


@addToClass(hou.Node)
def isEditable(self):
    """Check if this node is marked as an editable node inside an asset.

    Returns:
        bool
            Returns True if this node is contained inside an HDA and is
            marked as being editable, otherwise False.

    Raises: N/A

    """
    return _cpp_methods.isEditable(self)


@addToClass(hou.Node)
def isCompiled(self):
    """Check if this node is compiled.

    Returns:
        bool
            Returns True if this node is compiled, otherwise False.

    Raises: N/A

    This check can be used to determine if a node is compiled for Orbolt,
    or has somehow become compiled on its own.

    """
    return _cpp_methods.isCompiled(self)


@addToClass(hou.Node)
def getOpReferences(self, recurse=False):
    """Returns a tuple of nodes this node has references to.

    Args:
        recurse=False : (bool)
            Apply recurively to child nodes.

    Returns:
        tuple
            A tuple of hou.Node objects the node references.

    Raises: N/A

    """
    result = _cpp_methods.getExistingOpReferences(self, recurse)

    return _getNodesFromPaths(result)


@addToClass(hou.Node)
def getOpDependents(self, recurse=False):
    """Returns a tuple of nodes that reference this node.

    Args:
        recurse=False : (bool)
            Apply recurively to child nodes.

    Returns:
        tuple
            A tuple of hou.Node objects that reference this node.

    Raises: N/A

    """
    result = _cpp_methods.getExistingOpDependents(self, recurse)

    return _getNodesFromPaths(result)


@addToClass(hou.Node)
def creationTime(self):
    """Get the date and time the node was created.

    Returns:
        datetime.datetime
            A datetime object representing the creation date and time.

    Raises: N/A

    """
    return _getTimeFromOpInfo(self, "Created  Time:")


@addToClass(hou.Node)
def modifiedTime(self):
    """Get the date and time the node was last modified.

    Returns:
        datetime.datetime
            A datetime object representing the modification date and time.

    Raises: N/A

    """
    return _getTimeFromOpInfo(self, "Modified Time:")


@addToClass(hou.NodeType)
def setIcon(self, icon_name):
    """Set the node type's icon name.

    Args:
        icon_name : (str)
            The icon name to set.

    Returns: N/A

    Raises: N/A

    """
    return _cpp_methods.setIcon(self, icon_name)


@addToClass(hou.NodeType)
def setDefaultIcon(self):
    """Set this node type's icon name to its default value.

    Returns: N/A

    Raises: N/A

    """
    return _cpp_methods.setDefaultIcon(self)


@addToClass(hou.NodeType)
def isPython(self):
    """Check if this node type represents a Python operator.

    Returns:
        bool
            Returns True if the operator is a Python type, otherwise False.

    Raises: N/A

    """
    return _cpp_methods.isPython(self)


@addToClass(hou.NodeType)
def isSubnetType(self):
    """Check if this node type is the primary subnet operator for the table.

    Returns:
        bool
            Returns True if the node type can contain child nodes of
            the same type, otherwise False.

    Raises: N/A

    This is the operator type which is used as a default container for nodes.

    """
    return _cpp_methods.isSubnetType(self)


@addToClass(hou.Vector3)
def componentAlong(self, vector):
    """Calculate the component of this vector along another vector.

    Args:
        vector : (hou.Vector3)
            A vector to calculate a component along.

    Returns:
        float
            The component along the vector.

    Raises: N/A

    """
    # The component of vector A along B is: A dot (unit vector // to B).
    return self.dot(vector.normalized())


@addToClass(hou.Vector3)
def project(self, vector):
    """Calculate the vector projection of this vector onto another vector.

    Args:
        vector : (hou.Vector3)
            A vector to project onto.

    Returns:
        hou.Vector3
            The vector projection.

    Raises:
        hou.OperationFailed
            Raise this exception if the supplied vector is the
            zero vector.

    This is an orthogonal projection of this vector onto a straight line
    parallel to the supplied vector.

    """
    # The vector cannot be the zero vector.
    if vector == hou.Vector3():
        raise hou.OperationFailed("Supplied vector must be non-zero.")

    return vector.normalized() * self.componentAlong(vector)


@addToClass(hou.Vector2, hou.Vector3, hou.Vector4)
def isNan(self):
    """Check if this vector contains NaNs.

    Returns:
        bool
            Returns True if any of the vector's components are NaN, otherwise
            False.

    Raises: N/A

    """
    import math

    # Iterate over each component.
    for i in range(len(self)):
        # If this component is a NaN, return True.
        if math.isnan(self[i]):
            return True

    # Didn't find any NaNs, so return False.
    return False


@addToClass(hou.Vector3)
def getDual(self):
    """Returns the dual of this vector.

    Returns:
        hou.Matrix3
            The dual of the vector.

    Raises: N/A

    The dual is a matrix which acts like the cross product when multiplied by
    other vectors.

    """
    # The matrix that will be the dual.
    mat = hou.Matrix3()

    # Compute the dual.
    _cpp_methods.getDual(self, mat)

    return mat


@addToClass(hou.Matrix3, hou.Matrix4)
def isIdentity(self):
    """Check if this matrix is the identity matrix.

    Returns:
        bool
            Returns True if the matrix is the identity matrix, otherwise False.

    Raises: N/A

    """
    # We are a 3x3 matrix.
    if isinstance(self, hou.Matrix3):
        # Construct a new 3x3 matrix.
        m = hou.Matrix3()

        # Set it to be the identity.
        m.setToIdentity()

        # Compare the two.
        return self == m

    # Compare against the identity transform from hmath.
    return self == hou.hmath.identityTransform()


@addToClass(hou.Matrix4)
def setTranslates(self, translates):
    """Set the translation values of this matrix.

    Args:
        translates : (list|tuple|hou.Vector3)
            The new translation values.  This can be any sequence of three
            floats.

    Returns: N/A

    Raises: N/A

    """
    # The translations are stored in the first 3 columns of the last row of the
    # matrix.  To set the values we just need to set the corresponding columns
    # to the matching components in the vector.
    for i in range(3):
        self.setAt(3, i, translates[i])


@addToModule(hou.hmath)
def buildLookat(from_vec, to_vec, up):
    """Compute a lookat matrix.

    Args:
        from_vec : (hou.Vector3)
            The original vector.
        to_vec : (hou.Vector3)
            The target vector.
        up : (hou.Vector3)
            The up vector.

    Returns:
        hou.Matrix3
            The lookat rotation matrix.

    Returns: N/A

    This function will compute a rotation matrix which will provide the rotates
    needed for "from_vec" to look at "to_vec".

    The lookat matrix will have the -Z axis point at the "to_vec" point.  The Y
    axis will be pointing "up".

    """
    # Create the new matrix to return.
    mat = hou.Matrix3()

    # Calculate the lookat and stick it in the matrix.
    _cpp_methods.buildLookat(mat, from_vec, to_vec, up)

    return mat


@addToModule(hou.hmath)
def buildInstance(position, direction, pscale=1, scale=hou.Vector3(1,1,1),
                  up=hou.Vector3(0,1,0), rot=hou.Quaternion(0,0,0,1),
                  trans=hou.Vector3(0,0,0), orient=None):
    """Compute a transform to orient to a given direction at a given position
    and with a scale.

    Args:
        position : (hou.Vector3)
            The position of the instance.
        direction : (hou.Vector3)
            Direction to orient the +Z axis to.
        pscale=1 : (float)
            Uniform scale.
        scale=hou.Vector3(1,1,1) : (hou.Vector3):
            Non-uniform scale.
        up=hou.Vector3(0,1,0) : (hou.Vector3)
            Up vector of the instance.
        rot=hou.Quaternion(0,0,0,1) : (hou.Quaternion)
            Additional rotation.
        trans=hou.Vector3(0,0,0) : (hou.Vector3)
            Translation of the instance.
        orient=None : (hou.Quaternion)
            Orientation of the instance.

    Returns:
        hou.Matrix4
            The calculated instance matrix.

    Raises: N/A

    The up vector is optional and will orient the matrix to this up vector.  If
    no up vector is given, the Z axis will be oriented to point in the supplied
    direction.  If a rotation quaternion is specified, the orientation will be
    additionally transformed by the rotation.  If a translation is specified,
    the entire frame of reference will be moved by this translation (unaffected
    by the scale or rotation).  If an orientation quaternion is specified, the
    orientation (using the direction and up vector will not be performed and
    this orientation will instead be used to define an original orientation.

    """
    zero_vec = hou.Vector3()

    # Scale the non-uniform scale by the uniform scale.
    scale *= pscale
    # Construct the scale matrix.
    scale_matrix = hou.hmath.buildScale(scale)

    # Build a rotation matrix from the rotation quaternion.
    rot_matrix = hou.Matrix4(rot.extractRotationMatrix3())

    # Build a translation matrix from the position and the translation vector.
    trans_matrix = hou.hmath.buildTranslate(position + trans)

    # If an orientation quaternion is passed, construct a matrix from it.
    if orient is not None:
        alignment_matrix = hou.Matrix4(orient.extractRotationMatrix3())
    else:
        # If the up vector is not the zero vector, build a lookat matrix
        # between the direction and zero vectors using the up vector.
        if up != zero_vec:
            alignment_matrix = hou.Matrix4(
                buildLookat(direction, zero_vec, up)
            )
        # If the up vector is the zero vector, build a matrix from the
        # dihedral.
        else:
            alignment_matrix = zero_vec.matrixToRotateTo(direction)

    # Return the instance transform matrix.
    return scale_matrix * alignment_matrix * rot_matrix * trans_matrix


@addToModule(hou.hda)
def getMetaSource(file_path):
    """Get the meta install location for the file.

    Returns:
        str|None
            The meta location this definition is installed to, if any.  If the
            file is not installed, returns None.

    Raises: N/A

    This function determines where the specified .otl file is installed to in
    the current session.  Examples include "Scanned OTL Directories", "Current
    Hip File", "Fallback Libraries" or specific OPlibraries files.

    """
    if file_path not in hou.hda.loadedFiles():
        return None

    return _cpp_methods.getMetaSource(file_path)


@addToClass(hou.HDADefinition)
def metaSource(self):
    """Get the meta install location of this asset definition.

    Returns:
        str
            The meta location this definition is installed to.

    Raises: N/A

    This function determines where the contained .otl file is installed to in
    the current session.  Examples include "Scanned OTL Directories", "Current
    Hip File", "Fallback Libraries" or specific OPlibraries files.

    """
    return hou.hda.getMetaSource(self.libraryFilePath())

