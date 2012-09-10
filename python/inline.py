#
# Produced by:
#       Graham Thompson
#       captainhammy@gmail.com
#       www.captainhammy.com
#
# Name:         inline.py
#
# Comments:     Custom C++ functions to enhance HOM.
#
# Version:      1.0
#

# Standard Library Imports
import ctypes
import types

# Third Party Imports
import hou
import inlinecpp


def addMethod(*args,**kwargs):
    """This decorator converts the function into an unbound method and adds
    it to the specified class.
    
    specify the classes you want to add the function to in the *args.
    you can override the name using a kwargs argument "name"
    
    example:
    
        @addMethod(hou.PrimGroup, hou.PointGroup, name="copy")
        will add a function named "copy" to hou.PrimGroup and hou.PointGroup.
        
    """
    def decorator(func):
        for cls in args:
            if "name" in kwargs:
                use_name = kwargs["name"]
            else:
                use_name = func.__name__
            
            unbound_method = types.MethodType(func, None, cls)
            setattr(cls, use_name, unbound_method)
        return unbound_method
    return decorator


cpp_methods = inlinecpp.createLibrary("cpp_methods",
includes="""
#include <GA/GA_AttributeRefMap.h>
#include <GEO/GEO_Face.h>
#include <GQ/GQ_Detail.h>
#include <GU/GU_Detail.h>
#include <OP/OP_Node.h>
#include <PRM/PRM_Parm.h>
""",
structs=[("IntArray", "*i"),
         ("StringArray", "**c"),
         ("StringTuple", "*StringArray"),
         ("VertexMap", (("prims", "*i"), ("indices", "*i"))),
         ("Position3D", (("x", "d"), ("y", "d"), ("z", "d"))),
         ("BoundingBox", (("xmin", "d"), ("ymin", "d"), ("zmin", "d"), ("xmax", "d"), ("ymax", "d"), ("zmax", "d"))),
        ],
function_sources=[
"""
int createPoint(GU_Detail *gdp, UT_Vector3D *position)
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
IntArray createPoints(GU_Detail *gdp, int count)
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
void setVarmap(GU_Detail *gdp,
               const char **strings,
               int num_strings)
{
    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    UT_String                   value;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_DETAIL, "varmap");

    // If it doesn't exist, add it.
    if (attrib_gah.isInvalid())
        attrib_gah = gdp->createStringAttribute(GA_ATTRIB_DETAIL, "varmap");

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
void addVariableName(GU_Detail *gdp,
                     const char *attrib_name,
                     const char *var_name)
{
    gdp->addVariableName(attrib_name, var_name);
}
""",

"""
void removeVariableName(GU_Detail *gdp,
                        const char *var_name)
{
    gdp->removeVariableName(var_name);
}
""",

"""
bool renameAttribute(GU_Detail *gdp,
                     int attrib_type,
                     const char *from_name,
                     const char *to_name)
{
    GA_AttributeOwner owner = static_cast<GA_AttributeOwner>(attrib_type);
    return gdp->renameAttribute(owner, GA_SCOPE_PUBLIC, from_name, to_name);
}
""",

"""
int findPrimitiveByName(const GU_Detail *gdp,
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
        return prim->getNum();

    // Return -1 to indicate that no prim was found.
    return -1;
}
""",

"""
IntArray findAllPrimitivesByName(const GU_Detail *gdp,
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
        prim_nums.push_back((*prims_it)->getNum());

    return prim_nums;
}
""",

"""
void copyPointAttributeValues(GU_Detail *dest_gdp,
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
                dest_gah = dest_gdp->addPointAttrib(attr);

            // Add a mapping between the source and dest attributes.
            hmap.append(dest_gah.getAttribute(), attr);
        }
    }

    // Get the point offsets.
    srcOff = src_gdp->pointOffset(src_pt);
    destOff = src_gdp->pointOffset(dest_pt);

    // Copy the attribute value.
    hmap.copyValue(GA_ATTRIB_POINT,
                   destOff,
                   GA_ATTRIB_POINT,
                   srcOff);

}
""",

"""
void copyPrimAttributeValues(GU_Detail *dest_gdp,
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
                dest_gah = dest_gdp->addPrimAttrib(attr);

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
IntArray pointAdjacentPolygons(GU_Detail *gdp, int prim_num)
{
    std::vector<int>            prim_nums;

    GA_Offset                   primOff;
    GA_OffsetArray              prims;

    GA_OffsetArray::const_iterator prims_it;

    primOff = gdp->primitiveOffset(prim_num);

    gdp->getPointAdjacentPolygons(prims, primOff);

    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back(gdp->primitiveIndex(*prims_it));
    }

    return prim_nums;
}
""",

"""
IntArray edgeAdjacentPolygons(GU_Detail *gdp, int prim_num)
{
    std::vector<int>            prim_nums;

    GA_Offset                   primOff;
    GA_OffsetArray              prims;

    GA_OffsetArray::const_iterator prims_it;

    primOff = gdp->primitiveOffset(prim_num);

    gdp->getEdgeAdjacentPolygons(prims, primOff);

    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back(gdp->primitiveIndex(*prims_it));
    }

    return prim_nums;
}
""",

"""
IntArray connectedPrims(const GU_Detail *gdp, int pt_num)
{
    std::vector<int>    prim_nums;

    GA_Offset           ptOff;
    GA_OffsetArray      prims;

    GA_OffsetArray::const_iterator prims_it;

    ptOff = gdp->pointOffset(pt_num);

    gdp->getPrimitivesReferencingPoint(prims, ptOff);

    for (prims_it = prims.begin(); !prims_it.atEnd(); ++prims_it)
    {
        prim_nums.push_back(gdp->primitiveIndex(*prims_it));
    }

    return prim_nums;
}
""",

"""
IntArray connectedPoints(const GU_Detail *gdp, int pt_num)
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
                pt_nums.push_back(gdp->pointIndex(*pt_it));
        }
    }

    return pt_nums;
}
""",

"""
VertexMap referencingVertices(const GU_Detail *gdp, int pt_num)
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
StringArray primStringAttribValues(const GU_Detail *gdp,
                                   const char *attrib_name)
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
        result.push_back(s_t->getString(attrib, *it, 0));

    return result;
}
""",

"""
void setPrimStringAttribValues(GU_Detail *gdp,
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
int setSharedPrimStringAttrib(GU_Detail *gdp,
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
        group = gdp->findPrimitiveGroup(group_name);

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_PRIMITIVE, attrib_name);

    // If it doesn't exist, return 1 to indicate we have an invalid attribute.
    if (attrib_gah.isInvalid())
        return 1;

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
StringArray pointStringAttribValues(const GU_Detail *gdp,
                                    const char *attrib_name)
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
        result.push_back(s_t->getString(attrib, *it, 0));

    return result;
}
""",

"""
void setPointStringAttribValues(GU_Detail *gdp,
                                const char *attrib_name,
                                const char **values,
                                int num_values)
{
    GA_Attribute                *attrib;
    GA_RWAttributeRef           attrib_gah;
    const GA_AIFSharedStringTuple       *s_t;

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_POINT, attrib_name);

    // Get the actual attribute.
    attrib = attrib_gah.getAttribute();

    // Get a shared string tuple from the attribute.
    s_t = attrib->getAIFSharedStringTuple();

    int i = 0;
    for (GA_Iterator it(gdp->getPointRange()); !it.atEnd(); ++it)
    {
        s_t->setString(attrib, *it, values[i], 0);
        i++;
    }
}
""",

"""
int setSharedPointStringAttrib(GU_Detail *gdp,
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
        group = gdp->findPointGroup(group_name);

    // Try to find the string attribute.
    attrib_gah = gdp->findStringTuple(GA_ATTRIB_POINT, attrib_name);

    // If it doesn't exist, return 1 to indicate we have an invalid attribute.
    if (attrib_gah.isInvalid())
        return 1;

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
bool hasEdge(const GU_Detail *gdp,
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
void insertVertex(GU_Detail *gdp,
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
void deleteVertex(GU_Detail *gdp, unsigned prim_num, unsigned idx)
{
    GA_Offset                   primOff;

    GEO_Face                    *face;

    primOff = gdp->primitiveOffset(prim_num);

    face = (GEO_Face *)gdp->getPrimitiveList().get(primOff);

    face->deleteVertex(idx);
}
""",

"""
void setPoint(GU_Detail *gdp, unsigned prim_num, unsigned idx, unsigned pt_num)
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
Position3D baryCenter(const GU_Detail *gdp, unsigned prim_num)
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
double primitiveArea(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    const GA_Primitive         *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GA_Primitive *)gdp->getPrimitiveList().get(primOff);

    return prim->calcArea();
}
""",

"""
double perimeter(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    const GA_Primitive         *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GA_Primitive *)gdp->getPrimitiveList().get(primOff);

    return prim->calcPerimeter();
}
""",

"""
void reversePrimitive(const GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    GEO_Primitive               *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GEO_Primitive *)gdp->getPrimitiveList().get(primOff);

    return prim->reverse();
}
""",

"""
void makeUnique(GU_Detail *gdp, unsigned prim_num)
{
    GA_Offset                   primOff;

    GEO_Primitive               *prim;

    primOff = gdp->primitiveOffset(prim_num);

    prim = (GEO_Primitive *)gdp->getPrimitiveList().get(primOff);

    gdp->uniquePrimitive(prim);
}
""",

"""
BoundingBox boundingBox(const GU_Detail *gdp, unsigned prim_num)
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
BoundingBox primGroupBoundingBox(const GU_Detail *gdp, const char *group_name)
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
BoundingBox pointGroupBoundingBox(const GU_Detail *gdp, const char *group_name)
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
bool addNormalAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           n_gah;

    n_gah = gdp->addNormalAttribute(GA_ATTRIB_POINT);

    // Return true if the attribute was created.
    if (n_gah.isValid())
        return true;

    // False otherwise.
    return false;
}
""",

"""
bool addVelocityAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           v_gah;

    v_gah = gdp->addVelocityAttribute(GA_ATTRIB_POINT);

    // Return true if the attribute was created.
    if (v_gah.isValid())
        return true;

    // False otherwise.
    return false;
}
""",

"""
bool addPointDiffuseAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           diff_gah;

    diff_gah = gdp->addDiffuseAttribute(GA_ATTRIB_POINT);

    // Return true if the attribute was created.
    if (diff_gah.isValid())
        return true;

    // False otherwise.
    return false;
}
""",

"""
bool addPrimDiffuseAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           diff_gah;

    diff_gah = gdp->addDiffuseAttribute(GA_ATTRIB_PRIMITIVE);

    // Return true if the attribute was created.
    if (diff_gah.isValid())
        return true;

    // False otherwise.
    return false;
}
""",

"""
bool addVertexDiffuseAttribute(GU_Detail *gdp)
{
    GA_RWAttributeRef           diff_gah;

    diff_gah = gdp->addDiffuseAttribute(GA_ATTRIB_VERTEX);

    // Return true if the attribute was created.
    if (diff_gah.isValid())
        return true;

    // False otherwise.
    return false;
}
""",

"""
void computePointNormals(GU_Detail *gdp)
{
    gdp->normal();
}
""",

"""
void convexPolygons(GU_Detail *gdp, unsigned maxpts=3)
{
    gdp->convex(maxpts);
}
""",

"""
void destroyEmptyPointGroups(GU_Detail *gdp)
{
    gdp->destroyEmptyGroups(GA_ATTRIB_POINT);
}
""",

"""
void destroyEmptyPrimGroups(GU_Detail *gdp)
{
    gdp->destroyEmptyGroups(GA_ATTRIB_PRIMITIVE);
}
""",

"""
void destroyUnusedPoints(GU_Detail *gdp, const char *group_name)
{
    GA_PointGroup               *group = 0;

    // If we passed in a valid group, try to find it.
    if (group_name)
        group = gdp->findPointGroup(group_name);

    gdp->destroyUnusedPoints(group);
}
""",

"""
void consolidatePoints(GU_Detail *gdp,
                       double distance,
                       const char *group_name)
{
    GA_PointGroup               *group = 0;

    if (group_name)
        group = gdp->findPointGroup(group_name);

    gdp->fastConsolidatePoints(distance, group);
}
""",

"""
void uniquePoints(GU_Detail *gdp,
                  const char *group_name,
                  int group_type)
{
    GA_ElementGroup             *group = 0;

    if (group_name)
    {
        if (group_type)
            group = gdp->findPrimitiveGroup(group_name);
        else
            group = gdp->findPointGroup(group_name);
    }

    gdp->uniquePoints(group);
}
""",

"""
void toggle(GU_Detail *gdp,
            const char *group_name,
            int group_type,
            int elem_num)
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
void setEntries(GU_Detail *gdp,
                const char *group_name,
                int group_type)
{
    GA_ElementGroup             *group = 0;

    if (group_type)
        group = gdp->findPrimitiveGroup(group_name);
    else
        group = gdp->findPointGroup(group_name);

    group->setEntries();

}
""",

"""
void toggleEntries(GU_Detail *gdp,
                   const char *group_name,
                   int group_type)
{
    GA_ElementGroup             *group = 0;

    if (group_type)
        group = gdp->findPrimitiveGroup(group_name);
    else
        group = gdp->findPointGroup(group_name);

    group->toggleEntries();
}
""",

"""
void copyGroup(GU_Detail *gdp,
               int group_type,
               const char *group_name,
               const char *new_group_name)
{
    const GA_ElementGroup       *group;
    GA_ElementGroup             *new_group;

    // Primitive group.
    if (group_type)
    {
        group = gdp->findElementGroup(GA_ATTRIB_PRIMITIVE, group_name);
        new_group = gdp->createElementGroup(GA_ATTRIB_PRIMITIVE,
                                            new_group_name);
    }
    // Point group.
    else
    {
        group = gdp->findElementGroup(GA_ATTRIB_POINT, group_name);
        new_group = gdp->createElementGroup(GA_ATTRIB_POINT,
                                            new_group_name);
    }

    new_group->copyMembership(*group);
}
""",

"""
bool containsAny(const GU_Detail *gdp,
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
void primToPointGroup(GU_Detail *gdp,
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
            point_group->addOffset(*pt_it);
    }

    // Destroy the source group if necessary.
    if (destroy)
        gdp->destroyPrimitiveGroup(prim_group);
}
""",

"""
void pointToPrimGroup(GU_Detail *gdp,
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
            prim_group->addOffset(*prims_it);
    }

    // Destroy the source group if necessary.
    if (destroy)
        gdp->destroyPointGroup(point_group);
}
""",

"""
void clip(GU_Detail *gdp, UT_Vector3D *normal, float dist)
{
    UT_Vector3 dir(*normal);

    GQ_Detail                   *gqd = new GQ_Detail(gdp);

    gqd->clip(dir, dist, 0);
    delete gqd;
}
""",

"""
bool isInside(const UT_BoundingBoxD *bbox1, const UT_BoundingBoxD *bbox2)
{
    return bbox1->isInside(*bbox2);
}
""",

"""
bool intersects(UT_BoundingBoxD *bbox1, const UT_BoundingBoxD *bbox2)
{
    return bbox1->intersects(*bbox2);
}
""",

"""
bool computeIntersection(UT_BoundingBoxD *bbox1, const UT_BoundingBoxD *bbox2)
{
    return bbox1->computeIntersection(*bbox2);
}
""",

"""
void expandBounds(UT_BoundingBoxD *bbox, float dltx, float dlty, float dltz)
{
    bbox->expandBounds(dltx, dlty, dltz);
}
""",

"""
void addToMin(UT_BoundingBoxD *bbox, const UT_Vector3D *vec)
{
    bbox->addToMin(*vec);
}
""",

"""
void addToMax(UT_BoundingBoxD *bbox, const UT_Vector3D *vec)
{
    bbox->addToMax(*vec);
}
""",

"""
double boundingBoxArea(const UT_BoundingBoxD *bbox)
{
    return bbox->area();
}
""",

"""
double boundingBoxVolume(const UT_BoundingBoxD *bbox)
{
    return bbox->volume();
}
""",

"""
bool isParmDefault(OP_Node *node,
                   const char *parm_name,
                   int index)
{
    PRM_Parm &parm = node->getParm(parm_name);

    return parm.isDefault(index);
}
""",

"""
bool isParmTupleDefault(OP_Node *node,
                        const char *parm_name)
{
    PRM_Parm &parm = node->getParm(parm_name);

    return parm.isDefault();
}
""",

"""
StringArray getReferencingParms(OP_Node *node, const char *parm_name)
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

        parm_tuple->getTemplatePtr()->getChannelToken(chan, component_indices[i]);
        path += chan;

        result.push_back(path.toStdString());
    }

    if (result.size() == 0)
        result.push_back("");

    return result;
}
""",

"""
const char *inputLabel(OP_Node *node, int index)
{
    return node->inputLabel(index);
}
""",

"""
bool isContainedBy(const OP_Node *node, const OP_Node *parent)
{
    return node->getIsContainedBy(parent);
}
""",

"""
StringArray getExistingOpReferences(OP_Node *node, bool recurse)
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
        result.push_back("");

    return result;
}
""",

"""
StringArray getExistingOpDependents(OP_Node *node, bool recurse)
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
        result.push_back("");

    return result;
}
""",

"""
bool isMultiParm(OP_Node *node, const char *parm_name)
{
    PRM_Parm &parm = node->getParm(parm_name);

    return parm.isMultiParm();
}
""",

"""
void insertMultiParmItem(OP_Node *node, const char *parm_name, int idx)
{
    node->insertMultiParmItem(parm_name, idx);
}
""",

"""
void removeMultiParmItem(OP_Node *node, const char *parm_name, int idx)
{
    node->removeMultiParmItem(parm_name, idx);
}
""",

"""
StringTuple getMultiParmInstances(OP_Node *node, const char *parm_name)
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
            result.push_back("");

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

])

@addMethod(hou.Geometry)
def isReadOnly(self):
    """
    Check if the geometry is read only.

    Args: None

    Returns:
        (bool):
            Returns True if the geometry is read only, otherwise False.

    Raises: None

    """
    # Get a GU Detail Handle for the geometry.
    handle = self._guDetailHandle()
    # Check if the handle is read only.
    result = handle.isReadOnly()
    # Destroy the handle.
    handle.destroy()

    return result


@addMethod(hou.Geometry)
def varmap(self):
    """Get the varmap as a dictionary.

    This function returns a dictionary representing the varmap
    attribute whose keys are the attribute names and values are
    the variable names.

    Args: None

    Returns:
        (dict|None):
            A dictionary representing the varmap attribute, if
            it exists.  If the attribute does not exist, returns
            None.

    Raises: None

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


@addMethod(hou.Geometry)
def createPoint(self, position=None):
    """Create a new point, optionally located at a position.

    Args:
        position (hou.Vector3):
            The position to create the point at.  A value of None will
            create the point at the origin.

    Returns:
        (hou.Point):
            The newly created point.

    Raises: None

    """
    if position is None:
        position = hou.Vector3()

    result = cpp_methods.createPoint(self, position)

    return self.iterPoints()[result]


@addMethod(hou.Geometry)
def createPoints(self, count):
    """Create a specific number of new points.

    Args:
        count (int):
            The number of new points to create.

    Returns:
        (tuple):
            A tuple of the hou.Point objects created.

    Raises:
        hou.OperationFailed:
            Raise this exception if count is not greater than 0.

    """
    if count <= 0:
        raise hou.OperationFailed("Invalid number of points.")

    result = cpp_methods.createPoints(self, count)

    return self.globPoints(" ".join([str(i) for i in result]))


@addMethod(hou.Geometry)
def setVarmap(self, varmap_dict):
    """Set the varmap based on the dictionary.

    This function will create variable mappings between the keys
    and values of the dictionary.  If the attribute does not
    exist it will be created.

    Args:
        varmap_dict (dict):
            A dictionary of attribute and variable names to set
            the varmap as.

    Returns: None

    Raises: None

    """
    # Create varmap string mappings from the key/value pairs.
    strings = ["{0} -> {1}".format(attrib_name, var)
	       for attrib_name, var in varmap_dict.iteritems()]

    # Construct a ctypes string array to pass the values.
    arr = (ctypes.c_char_p * len(strings))()
    arr[:] = strings

    # Update the varmap.
    cpp_methods.setVarmap(self, arr, len(strings))


@addMethod(hou.Geometry)
def addVariableName(self, attrib, var_name):
    """Add a variable mapping to the attribute in the varmap.

    Args:
        attrib (hou.Attrib):
            The attribute to create a variable mapping for.
        var_name (string):
            The variable name to map to the attribute.

    Returns: None

    Raises: None

    """
    cpp_methods.addVariableName(self, attrib.name(), var_name)


@addMethod(hou.Geometry)
def removeVariableName(self, var_name):
    """Remove a variable mapping from the varmap.

    Args:
        var_name (string):
            The variable name to remove the mapping for.

    Returns: None

    Raises: None

    """
    cpp_methods.removeVariableName(self, var_name)

@addMethod(hou.Attrib,name="rename")
def renameAttribute(self, new_name):
    """Rename the attribute.

    Args:
        new_name (string):
            The new attribute name.
    
    Returns:
        (hou.Attrib|None):
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
    success = cpp_methods.renameAttribute(geometry,
                                          owner,
                                          self.name(),
                                          new_name)

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


@addMethod(hou.Geometry)
def findPrimByName(self,
                   name_to_match,
                   name_attribute="name",
                   match_number=0):
    """Find a primitive with a matching name attribute value.

    Args:
        name_to_match (string):
            The name attribute value to match.
        name_attribute (string):
            The attribute name to use.
        match_number (int):
            The match_numberth matching primitive to return.

    Returns:
        (hou.Primitive|None):
            A matching primitive, if found.  If no primitive
            is found, returns None.  None is also returned if
            match_number is greater than the number of matches
            found.

    Raises: None

    """
    # Try to find a primitive matching the name.
    result = cpp_methods.findPrimitiveByName(self,
                                             name_to_match,
                                             name_attribute,
                                             match_number)

    # If the result is -1, no prims were found so return None.
    if result == -1:
        return None

    #  Return the primitive.
    return self.iterPrims()[result]

    
@addMethod(hou.Geometry)
def findAllPrimsByName(self, name_to_match, name_attribute="name"):
    """Find all primitives with a matching name attribute value.

    Args:
        name_to_match (string):
            The name attribute value to match.
        name_attribute (string):
            The attribute name to use.

    Returns:
        (tuple)
            A tuple of hou.Prim objects whose attribute values
            match.

    Raises: None

    """
    # Try to find matching primitives.
    result = cpp_methods.findAllPrimitivesByName(self,
                                                 name_to_match,
                                                 name_attribute)

    # Return a tuple of the matching primitives if any were found.
    if result:
        return self.globPrims(' '.join([str(i) for i in result]))

    # If none were found, return an empty tuple.
    return ()

@addMethod(hou.Point, name="copyAttributeValues")
def copyPointAttributeValues(self, source_point, attributes):
    """Copy the attribute values from the source point.

    If the attributes do not exist on the destination point they
    will be created.

    Args:
        source_point (hou.Point):
            The point to copy the attribute values from.
        attributes (list):
            A list of hou.Attrib objects representing point attributes
            on the source geometry.

    Returns: None

    Raises: None

    """
    # Get the source point's geometry.
    source_geometry = source_point.geometry()

    # Get the attribute names, ensuring we only use point attributes
    # on the source point's geometry.
    attrib_names = [attrib.name() for attrib in attributes
                    if attrib.type() == hou.attribType.Point and
                    attrib.geometry().sopNode() == source_geometry.sopNode()]

    # The number of attributes.
    num_attribs = len(attrib_names)

    # Construct an object we can pass through ctypes as a const char **.
    arr = (ctypes.c_char_p * num_attribs)()
    arr[:] = attrib_names

    # Copy the values.
    cpp_methods.copyPointAttributeValues(self.geometry(),
                                         self.number(),
                                         source_geometry,
                                         source_point.number(),
                                         arr,
                                         num_attribs)

@addMethod(hou.Prim, name="copyAttributeValues")
def copyPrimAttributeValues(self, source_prim, attributes):
    """Copy the attribute values from the source primitive.

    If the attributes do not exist on the destination primitive they
    will be created.

    Args:
        source_prim (hou.Prim):
            The primitive to copy the attribute values from.
        attributes (list):
            A list of hou.Attrib objects representing primitive attributes
            on the source geometry.

    Returns: None

    Raises: None

    """
    # Get the source primitive's geometry.
    source_geometry = source_prim.geometry()

    # Get the attribute names, ensuring we only use primitive attributes
    # on the source primitive's geometry.
    attrib_names = [attrib.name() for attrib in attributes
                    if attrib.type() == hou.attribType.Prim and
                    attrib.geometry().sopNode() == source_geometry.sopNode()]

    # The number of attributes.
    num_attribs = len(attrib_names)

    # Construct an object we can pass through ctypes as a const char **.
    arr = (ctypes.c_char_p * num_attribs)()
    arr[:] = attrib_names

    # Copy the values.
    cpp_methods.copyPrimAttributeValues(self.geometry(),
                                        self.number(),
                                        source_geometry,
                                        source_prim.number(),
                                        arr,
                                        num_attribs)

@addMethod(hou.Point)
def connectedPrims(self):
    """Get all primitives that reference the point.

    Args: None

    Returns:
        (tuple):
            A tuple of hou.Prim objects that reference the point.

    Raises: None

    """
    # Get the geometry the point belongs to.
    geometry = self.geometry()
    # Get a list of primitive numbers that reference the point.
    result = cpp_methods.connectedPrims(geometry,
                                        self.number())

    return geometry.globPrims(' '.join([str(i) for i in result]))


@addMethod(hou.Point)
def connectedPoints(self):
    """Get all points that share an edge with the point.

    Args: None

    Returns:
        (tuple):
            A tuple of hou.Point objects that share an edge with
            the point.

    Raises: None

    """
    # Get the geometry the point belongs to.
    geometry = self.geometry()

    # Get a list of point numbers that are connected to the point.
    result = cpp_methods.connectedPoints(geometry,
                                         self.number())

    # Glob for the points and return them.
    return geometry.globPoints(' '.join([str(i) for i in result]))

    
@addMethod(hou.Point)
def referencingVertices(self):
    """Get all the vertices that reference the point.

    Args: None

    Returns:
        (tuple):
            A tuple of hou.Vertex objects that reference the point.

    Raises: None

    """
    # Get the geometry the point belongs to.
    geometry = self.geometry()

    # Get an object containing primitive and vertex index information.
    result = cpp_methods.referencingVertices(geometry,
                                             self.number())

    # Construct a list of vertex strings.  Each element has the format:
    # {prim_num}v{vertex_index}.
    vertex_strings = ["{0}v{1}".format(prim, idx)
                      for prim, idx in zip(result.prims, result.indices)]

    # Glob for the vertices and return them.
    return geometry.globVertices(' '.join(vertex_strings))

    
@addMethod(hou.Geometry)
def primStringAttribValues(self, name):
    """Return a tuple of strings containing one attribute's values for
    all the primitives.

    Args:
        name (string):
            The name of the primitive attribute.

    Returns:
        (tuple):
            A tuple of strings representing the attribute values for
            each primitive.

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute name is invalid or
            the attribute is not a string.

    """
    attrib = self.findPrimAttrib(name)
    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    return cpp_methods.primStringAttribValues(self, name)


@addMethod(hou.Geometry)
def setPrimStringAttribValues(self, name, values):
    """Set the string attribute values for all primitives.

    Args:
        name (string):
            The name of the primitive attribute.
        values (tuple):
            A tuple of strings representing the attribute values for
            each primitive.

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute name is invalid,
            the attribute is not a string, or the array of values
            is not the correct size.

    """
    attrib = self.findPrimAttrib(name)
    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    if len(values) != len(self.iterPrims()):
        raise hou.OperationFailed("Incorrect attribute value sequence size.")

    # Construct a ctypes string array to pass the values.
    arr = (ctypes.c_char_p * len(values))()
    arr[:] = values

    return cpp_methods.setPrimStringAttribValues(self,
                                                 name,
                                                 arr,
                                                 len(values))


@addMethod(hou.Geometry)
def setSharedPrimStringAttrib(self, attribute, value, group=None):
    """Set a string attribute value for primitives.

    If group is None, all primitives will have receive the value.  If
    a group is passed, only the primitives in the group will be set.

    Args:
        attribute (hou.Attrib):
            The string attribute to set.
        value (string):
            The attribute value to set.
        group (hou.PrimGroup):
            An optional primitive group to specify which primitives
            to set.

    Returns: None

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute is invalid.

    """
    # If the group is valid, use that group's name.
    if group:
        group_name = group.name()
    # If not, pass an empty string to signify no group.
    else:
        group_name = ""

    result = cpp_methods.setSharedPrimStringAttrib(self,
                                                   attribute.name(),
                                                   value,
                                                   group_name)

    # Check the result for errors.
    if result == 1:
        raise hou.OperationFailed("Invalid attribute.")


@addMethod(hou.Geometry)
def pointStringAttribValues(self, name):
    """Return a tuple of strings containing one attribute's values for
    all the points.

    Args:
        name (string):
            The name of the point attribute.

    Returns:
        (tuple):
            A tuple of strings representing the attribute values for
            each point.

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute name is invalid or
            the attribute is not a string attribute.

    """
    attrib = self.findPointAttrib(name)
    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    return cpp_methods.pointStringAttribValues(self, name)

    
@addMethod(hou.Geometry)
def setPointStringAttribValues(self, name, values):
    """Set the string attribute values for all points.

    Args:
        name (string):
            The name of the point attribute.
        values (tuple):
            A tuple of strings representing the attribute values for
            each point.

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute name is invalid,
            the attribute is not a string, or the array of values
            is not the correct size.

    """
    attrib = self.findPointAttrib(name)
    if attrib is None:
        raise hou.OperationFailed("Invalid attribute name.")

    if attrib.dataType() != hou.attribData.String:
        raise hou.OperationFailed("Attribute must be a string.")

    if len(values) != len(self.iterPoints()):
        raise hou.OperationFailed("Incorrect attribute value sequence size.")

    # Construct a ctypes string array to pass the values.
    arr = (ctypes.c_char_p * len(values))()
    arr[:] = values

    return cpp_methods.setPointStringAttribValues(self,
                                                  name,
                                                  arr,
                                                  len(values))


@addMethod(hou.Geometry)
def setSharedPointStringAttrib(self, attribute, value, group=None):
    """Set a string attribute value for points.

    If group is None, all points will have receive the value.  If
    a group is passed, only the points in the group will be set.

    Args:
        attribute (hou.Attrib):
            The string attribute to set.
        value (string):
            The attribute value to set.
        group (hou.PointGroup):
            An optional point group to specify which points to set.

    Returns: None

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute is invalid.

    """
    # If the group is valid, use that group's name.
    if group:
        group_name = group.name()
    # If not, pass an empty string to signify no group.
    else:
        group_name = ""

    result = cpp_methods.setSharedPointStringAttrib(self,
                                                    attribute.name(),
                                                    value,
                                                    group_name)

    # Check the result for errors.
    if result == 1:
        raise hou.OperationFailed("Invalid attribute.")


@addMethod(hou.Face)
def hasEdge(self, point1, point2):
    """Test if a face has an edge between two points.

    Args:
        point1 (hou.Point):
            An edge point.
        point2 (hou.Point):
            An edge point.

    Returns:
        (bool):
            Returns True if an edge exists between the two points,
            otherwise False.

    Raises: None

    """
    # Test for the edge.
    return cpp_methods.hasEdge(self.geometry(),
                               self.number(),
                               point1.number(),
                               point2.number())

                                   
@addMethod(hou.Face)
def insertVertex(self, point, index):
    """Insert a vertex referencing the point into the face at a specific index.

    Args:
        point (hou.Point):
            The point the vertex will be attached to.
        index (int):
            The index of the vertex to insert.

    Returns: None

    Raises: None

    """
    # Insert the vertex.
    cpp_methods.insertVertex(self.geometry(),
                             self.number(),
                             point.number(),
                             index)

                                 
@addMethod(hou.Face)
def deleteVertex(self, index):
    """Delete the vertex at the specified index.

    Args:
        index (int):
            The index of the vertex to delete.

    Returns: None

    Raises: None

    """
    # Delete teh vertex.
    cpp_methods.deleteVertex(self.geometry(),
                             self.number(),
                             index)

                                 
@addMethod(hou.Prim)
def setPoint(self, index, point):
    """Set the vertex, at the specified index, to be attached to the point.

    Args:
        index (int):
            The index of the vertex to modify.
        point (hou.Point):
            The point to attach the vertex to.

    Returns: None

    Raises: None

    """
    # Delete teh vertex.
    cpp_methods.setPoint(self.geometry(),
                         self.number(),
                         index,
                         point.number())

                             
@addMethod(hou.Prim)
def baryCenter(self):
    """Get the barycenter of the primitive.

    Args: None

    Returns:
        (hou.Vector3):
            The barycenter of the primitive.

    Raises: None

    """
    # Get the Position3D object representing the barycenter.
    pos = cpp_methods.baryCenter(self.geometry(),
                                 self.number())

    # Construct a vector and return it.
    return hou.Vector3(pos.x, pos.y, pos.z)


@addMethod(hou.Prim, name="area")
def primitiveArea(self):
    """Get the area of the primitive.

    Args: None

    Returns:
        (double):
            The area of the primitive.

    Raises: None

    """
    # Calculate and return the area.
    return cpp_methods.primitiveArea(self.geometry(),
                                     self.number())

                                     
@addMethod(hou.Prim)
def perimeter(self):
    """Get the perimeter of the primitive.

    Args: None

    Returns:
        (double):
            The perimeter of the primitive.

    Raises: None

    """
    # Calculate and return the perimeter.
    return cpp_methods.perimeter(self.geometry(),
                                 self.number())


@addMethod(hou.Prim,name="reverse")
def reversePrim(self):
    """Reverse the order of vertices.

    Args: None

    Returns: None

    Raises: None

    """
    return cpp_methods.reversePrimitive(self.geometry(),
                               self.number())


@addMethod(hou.Prim)
def makeUnique(self):
    """Unique all the points that are in the primitive.

    This function will unique all the points even if they are
    referenced by other primitives.

    Args: None

    Returns: None

    Raises: None

    """
    return cpp_methods.makeUnique(self.geometry(),
                                  self.number())


@addMethod(hou.Prim)
def boundingBox(self):
    """Get the bounding box of the primitive.

    Args: None

    Returns:
        (hou.BoundingBox):
            The bounding box of the primitive.

    Raises: None

    """
    # Calculate the bounds for the primitive.
    bounds = cpp_methods.boundingBox(self.geometry(),
                                     self.number())

    # Construct and return a hou.BoundingBox object.
    return hou.BoundingBox(bounds.xmin, bounds.ymin, bounds.zmin,
                           bounds.xmax, bounds.ymax, bounds.zmax)


@addMethod(hou.PrimGroup, hou.PointGroup ,name="boundingBox")
def groupBoundingBox(self):
    """Get the bounding box of the group.

    Args: None

    Returns:
        (hou.BoundingBox):
            The bounding box of the group.

    Raises: None

    """
    # Calculate the bounds for the group.
    if isinstance(self, hou.PrimGroup):
        bounds = cpp_methods.primGroupBoundingBox(self.geometry(),
                                                  self.name())
    else:
        bounds = cpp_methods.pointGroupBoundingBox(self.geometry(),
                                                   self.name())

    # Construct and return a hou.BoundingBox object.
    return hou.BoundingBox(bounds.xmin, bounds.ymin, bounds.zmin,
                           bounds.xmax, bounds.ymax, bounds.zmax)


@addMethod(hou.Geometry, name="addPointNormals")
def addNormalAttribute(self):
    """Add point normals to the geometry.

    Args: None

    Returns:
        hou.Attrib:
            Returns the newly created point attribute.

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute was not created.

    """
    result = cpp_methods.addNormalAttribute(self)

    if result:
        return self.findPointAttrib("N")

    raise hou.OperationFailed("Could not add normal attribute.")


@addMethod(hou.Geometry, name="addPointVelocity")
def addVelocityAttribute(self):
    """Add point velocity to the geometry.

    Args: None

    Returns:
        hou.Attrib:
            Returns the newly created point attribute.

    Raises:
        hou.OperationFailed:
            Raise this exception if the attribute was not created.

    """
    result = cpp_methods.addVelocityAttribute(self)

    if result:
        return self.findPointAttrib("v")

    raise hou.OperationFailed("Could not add velocity attribute.")


@addMethod(hou.Geometry)
def addColorAttribute(self, attrib_type):
    """Add a color (Cd) attribute to the geometry.

    Point, primitive and vertex colors are supported.

    Args:
        attrib_type (hou.attribType):
            A hou.attribType value to specify if the attribute
            should be a point, primitive or vertex attribute.

    Returns:
        hou.Attrib:
            Returns the newly created point attribute.

    Raises:
        hou.TypeError:
            Raise this exception if attribute_type is not a valid.
            type.
        hou.OperationFailed:
            Raise this exception if the attribute was not created.

    """
    # Try to add a point Cd attribute.
    if attrib_type == hou.attribType.Point:
        result = cpp_methods.addPointDiffuseAttribute(self)

        if result:
            return self.findPointAttrib("Cd")

    # Try to add a primitive Cd attribute.
    elif attrib_type == hou.attribType.Prim:
        result = cpp_methods.addPrimDiffuseAttribute(self)

        if result:
            return self.findPrimAttrib("Cd")

    # Try to add a vertex Cd attribute.
    elif attrib_type == hou.attribType.Vertex:
        result = cpp_methods.addVertexDiffuseAttribute(self)

        if result:
            return self.findVertexAttrib("Cd")

    # The type didn't match any of the valid ones so we should
    # throw an exception.
    else:
        raise hou.TypeError("Invalid attribute type.")

    # We didn't create an attribute, so throw an exception.
    raise hou.OperationFailed("Could not add Cd attribute.")


@addMethod(hou.Geometry)
def computePointNormals(self):
    """Computes the point normals for the geometry.

    This is equivalent to using a Point sop, selecting 'Add Normal'
    and leaving the default values.  It will add the 'N' attribute
    if it does not exist.

    Args: None

    Returns: None

    Raises: None

    """
    cpp_methods.computePointNormals(self)


@addMethod(hou.Geometry)
def convex(self, max_points=3):
    """Convex the geometry into polygons with a certain number of
    points.

    This operation is similar to using the Divide SOP and setting
    the 'Maximum Edges'.

    Args:
        max_points (int):
            The maximum number of points for each polygon.

    Returns: None

    Raises: None

    """
    cpp_methods.convexPolygons(self, max_points)


@addMethod(hou.Geometry)
def destroyEmptyPointGroups(self):
    """Remove any empty point groups.

    Args: None

    Returns: None

    Raises: None

    """
    cpp_methods.destroyEmptyPointGroups(self)


@addMethod(hou.Geometry)
def destroyEmptyPrimGroups(self):
    """Remove any empty primitive groups.

    Args: None

    Returns: None

    Raises: None

    """
    cpp_methods.destroyEmptyPrimGroups(self)


@addMethod(hou.Geometry)
def destroyUnusedPoints(self, group=None):
    """Remove any unused points.

    If group is not None, only unused points within the group are
    removed.

    Args:
        group (hou.PointGroup):
            An optional point group to restrict the removal.

    Returns: None

    Raises: None

    """
    if group is not None:
        cpp_methods.destroyUnusedPoints(self, group.name())
    else:
        cpp_methods.destroyUnusedPoints(self, 0)


@addMethod(hou.Geometry)
def consolidatePoints(self, distance=0.001, group=None):
    """Consolidate points within a specified distance.

    If group is not None, only points in that group are consolidated.

    Args:
        group (hou.PointGroup):
            An optional point group to restrict the consolidation.

    Returns: None

    Raises: None

    """
    if group is not None:
        cpp_methods.consolidatePoints(self, distance, group.name())
    else:
        cpp_methods.consolidatePoints(self, distance, 0)


@addMethod(hou.Geometry)
def uniquePoints(self, group=None):
    """Unique all points in the geometry.

    If a point group is specified, only points in that group are
    uniqued.  If a primitive group is specified, only those
    primitives will have their points uniqued.

    Args:
        group (hou.PointGroup|hou.PrimGroup):
            An optional group to restrict the uniqueing to.

    Returns: None

    Raises: None

    """
    if group is not None:
        # Check the group type.
        if isinstance(group, hou.PrimGroup):
            group_type = 1
        # hou.PointGroup
        else:
            group_type = 0

        cpp_methods.uniquePoints(self, group.name(), group_type)

    else:
        cpp_methods.uniquePoints(self, 0, 0)

@addMethod(hou.PointGroup,name="toggle")
def togglePoint(self, point):
    """Toggle group membership for a point.

    If the point is a part of the group, it will be removed.  If it
    isn't, it will be added.

    Args:
        point (hou.Point):
            The point whose membership to toggle.

    Returns: None

    Raises: None

    """
    geometry = self.geometry()

    cpp_methods.toggle(geometry, self.name(), 0, point.number())


@addMethod(hou.PrimGroup ,name="toggle")
def togglePrim(self, prim):
    """Toggle group membership for a primitive.

    If the primitive is a part of the group, it will be removed.  If it
    isn't, it will be added.

    Args:
        point (hou.prim):
            The primitive whose membership to toggle.

    Returns: None

    Raises: None

    """
    geometry = self.geometry()

    cpp_methods.toggle(geometry, self.name(), 1, prim.number())


@addMethod(hou.PrimGroup,hou.PointGroup)
def toggleEntries(self):
    """Toggle group membership for all elements in the group.

    All elements not in the group will be added to it and all
    that were in it will be removed.

    Args: None

    Returns: None

    Raises: None

    """
    geometry = self.geometry()

    if isinstance(self, hou.PrimGroup):
        group_type = 1
    # hou.PointGroup
    else:
        group_type = 0

    cpp_methods.toggleEntries(geometry, self.name(), group_type)


@addMethod(hou.PrimGroup, hou.PointGroup, name="copy")
def copyGroup(self, new_group_name):
    """Create a group under the new name with the same membership.

    Args:
        new_group_name (string):
            The new group name.

    Returns: None

    Raises:
        hou.OperationFailed:
            Raise this exception if the new group name is the same
            as the source group name, or a group with the new name
            already exists.

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
    cpp_methods.copyGroup(geometry, group_type, self.name(), new_group_name)


@addMethod(hou.PrimGroup, hou.PointGroup, name="containsAny")
def primGroupContainsAny(self, group):
    """Returns whether or not any prims in the group are in this group.

    Args:
        group (hou.PrimGroup):
            A prim group which may have one or more prims in
            this group.

    Returns:
        (bool):
            Returns True if the group has one or more primitives that are
            in this group, otherwise False.

    Raises: None

    """
    geometry = self.geometry()

    return cpp_methods.containsAny(geometry, self.name(), group.name(), 1)



@addMethod(hou.PrimGroup)
def convertToPointGroup(self, new_group_name=None, destroy=True):
    """Create a new hou.Point group from this primitive group.

    The group will contain all the points referenced by all the vertices
    of the primitives in the group.

    Args:
        new_group_name (string):
            The name of the new point group.  If None, the point group
            will receive the same name as the source group.
        remove (bool):
            Destroy the source primitive group.

    Returns:
        (hou.PointGroup):
            The newly created point group.

    Raises:
        hou.OperationFailed:
            This exception is raised if there is already a point group
            with the specified name.

    """
    geometry = self.geometry()

    if new_group_name is None:
        new_group_name = self.name()

    if geometry.findPointGroup(new_group_name):
        raise hou.OperationFailed("Group already exists.")

    cpp_methods.primToPointGroup(geometry,
                                 self.name(),
                                 new_group_name,
                                 destroy)

    return geometry.findPointGroup(new_group_name)


@addMethod(hou.PointGroup)
def convertToPrimGroup(self, new_group_name=None, destroy=True):
    """Create a new hou.Prim group from this point group.

    The group will contain all the primitives which have vertices
    referencing any of the points in the group.

    Args:
        new_group_name (string):
            The name of the new prim group.  If None, the prim group
            will receive the same name as the source group.
        remove (bool):
            Destroy the source point group.

    Returns:
        (hou.PrimGroup):
            The newly created prim group.

    Raises:
        hou.OperationFailed:
            This exception is raised if there is already a prim group
            with the specified name.

    """
    geometry = self.geometry()

    if new_group_name is None:
        new_group_name = self.name()

    if geometry.findPrimGroup(new_group_name):
        raise hou.OperationFailed("Group already exists.")

    cpp_methods.pointToPrimGroup(geometry,
                                 self.name(),
                                 new_group_name,
                                 destroy)

    return geometry.findPrimGroup(new_group_name)

    
@addMethod(hou.Geometry)
def clip(self, normal, dist):
    """Clip the geometry along a plane.

    Args:
        normal (hou.Vector3):
            The normal of the plane to clip with.
        dist (float):
            The distance along the normal to clip at.

    Returns: None

    """

    cpp_methods.clip(self, normal.normalized(), dist)


@addMethod(hou.BoundingBox)
def isInside(self, bbox):
    """Determine if the bounding box is totally enclosed by the other box.

    Args:
        bbox (hou.BoundingBox):
            A bounding box that might enclose this box.

    Returns:
        (bool):
            Returns True if the bounding box encloses this box,
            otherwise False.

    Raises: None

    """
    return cpp_methods.isInside(self, bbox)

    
@addMethod(hou.BoundingBox)
def intersects(self, bbox):
    """Determine if the bounding boxes intersect.

    Args:
        bbox (hou.BoundingBox):
            A bounding box to test intersection with.

    Returns:
        (bool):
            Returns True if the two bounding boxes intersect,
            otherwise False.

    Raises: None

    """
    return cpp_methods.intersects(self, bbox)

    
@addMethod(hou.BoundingBox)
def computeIntersection(self, bbox):
    """Changes the bounds to be those of the intersection of this box
    and the supplied box.

    Args:
        bbox (hou.BoundingBox):
            A bounding box to compute the intersection of.

    Returns:
        (bool):
            Returns True if the two bounding boxes intersect,
            otherwise False.

    Raises: None

    """
    return cpp_methods.computeIntersection(self, bbox)


@addMethod(hou.BoundingBox)
def expandBounds(self, dltx, dlty, dltz):
    """Expand the min and max bounds in each direction by the axis delta.

    Args:
        dltx (float):
            The amount to expand each X axis bounds.
        dlty (float):
            The amount to expand each Y axis bounds.
        dltz (float):
            The amount to expand each Z axis bounds.

    Returns: None

    Raises: None

    """
    cpp_methods.expandBounds(self, dltx, dlty, dltz)

    
@addMethod(hou.BoundingBox)
def addToMin(self, vec):
    """Add values to the minimum bounds.

    Args:
        vec (hou.Vector3):
            The amount to expand the minimum bound values.

    Returns: None

    Raises: None

    """
    cpp_methods.addToMin(self, vec)

    
@addMethod(hou.BoundingBox)
def addToMax(self, vec):
    """Add values to the maximum bounds.

    Args:
        vec (hou.Vector3):
            The amount to expand the maximum bound values.

    Returns: None

    Raises: None

    """
    cpp_methods.addToMax(self, vec)


@addMethod(hou.BoundingBox, name = "area")
def boundingBoxArea(self):
    """Calculate the area of the bounding box.

    Args: None

    Returns:
        (float):
            The area of the surface of the bounding box.

    Raises: None

    """
    cpp_methods.boundingBoxArea(self)

    
@addMethod(hou.BoundingBox, name = "volume")
def boundingBoxVolume(self):
    """Calculate the volume of the bounding box.

    Args: None

    Returns:
        (float):
            The volume of the bounding box.

    Raises: None

    """
    cpp_methods.boundingBoxVolume(self)


@addMethod(hou.Parm, name ="isDefault")
def isParmDefault(self):
    """Returns if a parameter is at its default value.

    Args: None

    Returns:
        (bool):
            Returns if the parameter is at its default value.

    Raises: None

    """
    # Get the node.
    node = self.node()
    # Get the index of the parameter.
    index = self.componentIndex()

    # Pass in the tuple name since we have to access the actual parm
    # by index.
    return cpp_methods.isParmDefault(node,
                                     self.tuple().name(),
                                     index)

@addMethod(hou.ParmTuple, name ="isDefault")
def isParmTupleDefault(self):
    """Returns if parameter tuple is at its default values.

    Args: None

    Returns:
        (bool):
            Returns if the parameter tuple is at its default values.

    Raises: None

    """
    # Get the node.
    node = self.node()

    return cpp_methods.isParmTupleDefault(node,
                                          self.name())


@addMethod(hou.Parm)
def getReferencingParms(self):
    """Returns a tuple of parameters that reference this parameter.

    Args: None

    Returns:
        (tuple):
            A tuple of referencing hou.Parm objects.

    Raises: None

    """
    # Get the node.
    node = self.node()

    # Get any paths to referencing parms.
    result = cpp_methods.getReferencingParms(node,
                                             self.name())

    # Create a tuple of parms.
    return tuple([hou.parm(parm_path) for parm_path in result
                  if parm_path])


@addMethod(hou.Node)
def inputLabel(self, index):
    """Returns the input label for the index.

    Args:
        index (int):
            The input index.

    Returns:
        (string):
            The label for the input.

    Raises:
        hou.IndexError:
            Raise this exception if the index is out of
            range.

    """
    if index not in range(0, self.nodeType.maxNumInputs()):
        raise IndexError("Index out of range.")

    return cpp_methods.inputLabel(self, index)

    
@addMethod(hou.Node)
def isContainedBy(self, node):
    """Test if this node is a contained within the node.

    Args:
        node (hou.Node):
            A node that may contain this node.

    Returns:
        (bool):
            Returns True if this node is contained in the node,
            otherwise False.

    Raises: None

    """
    return cpp_methods.isContainedBy(self, node)

    
@addMethod(hou.Node)
def getExistingOpReferences(self, recurse=False):
    """Returns a tuple of nodes this node has references to.

    Args:
        recurse (bool):
            Apply recurively to child nodes.

    Returns:
        (tuple):
            A tuple of hou.Node objects the node references.

    Raises: None

    """
    result = cpp_methods.getExistingOpReferences(self, recurse)

    return tuple([hou.node(path) for path in result if path])

    
@addMethod(hou.Node)
def getExistingOpDependents(self, recurse=False):
    """Returns a tuple of nodes that reference this node.

    Args:
        recurse (bool):
            Apply recurively to child nodes.

    Returns:
        (tuple):
            A tuple of hou.Node objects that reference this node.

    Raises: None

    """
    result = cpp_methods.getExistingOpDependents(self, recurse)

    return tuple([hou.node(path) for path in result if path])


@addMethod(hou.Parm, hou.ParmTuple)
def isMultiParm(self):
    """Check if a parameter is a multiparm.

    Args: None

    Returns:
        (bool):
            Returns True if the parm is a multiparm, otherwise False.

    Raises: N/A

    """
    node = self.node()

    return cpp_methods.isMultiParm(node, self.name())


@addMethod(hou.Parm, hou.ParmTuple)
def insertMultiParmItem(self, index):
    """Insert a multiparm item at the specified index.

    This is the equivalent of hitting the Insert Before button (+)
    on a multiparm to insert a new folder at that location.

    Args:
        index (int):
            The index for the new item.

    Returns: None

    Raises:
        hou.OperationFailed:
            This exception is raised if the parameter is not a
            multiparm.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    cpp_methods.insertMultiParmItem(node, self.name(), index)

    
@addMethod(hou.Parm, hou.ParmTuple)
def removeMultiParmItem(self, index):
    """Remove a multiparm item at the specified index.

    This is the equivalent of hitting the Remove button (x) on
    a multiparm to remove a folder.

    Args:
        index (int):
            The index to remove.

    Returns: None

    Raises:
        hou.OperationFailed:
            This exception is raised if the parameter is not a
            multiparm.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    cpp_methods.removeMultiParmItem(node, self.name(), index)

    
@addMethod(hou.Parm, hou.ParmTuple)
def getMultiParmInstances(self):
    """Return all the parameters in the multiparm block.

    The parameters are returned as a tuple of parameters based
    on each instance.

    Args: None

    Returns:
        (tuple):
            A tuple of tuples representing the parameters of each
            multiparm instance.

    Raises:
        hou.OperationFailed:
            This exception is raised if the parameter is not a
            multiparm.

    """
    node = self.node()

    if not self.isMultiParm():
        raise hou.OperationFailed("Not a multiparm.")

    # Get the multiparm parameter names.
    result = cpp_methods.getMultiParmInstances(node, self.name())

    multi_parms = []

    # Iterate over each multiparm instance.
    for block in result:
        # Build a list of parameters in the instance.
        parms = [node.parm(parm_name) for parm_name in block if parm_name]
        multi_parms.append(tuple(parms))

    return tuple(multi_parms)

    
@addMethod(hou.Parm, hou.ParmTuple)
def getMultiParmInstanceValues(self):
    """Return all the parameter values in the multiparm block.

    The values are returned as a tuple of values based
    on each instance.

    Args: None

    Returns:
        (tuple):
            A tuple of tuples representing the values of each
            multiparm instance.

    Raises:
        hou.OperationFailed:
            This exception is raised if the parameter is not a
            multiparm.

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

