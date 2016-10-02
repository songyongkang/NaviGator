#!/usr/bin/env python
from navigator_msgs.msg import PerceptionObject
from navigator_msgs.srv import PerceptionObjectService, PerceptionObjectServiceResponse
from navigator_msgs.msg import ClassifyUnknownAction, ClassifyUnknownGoal, ClassifyUnknownResult, ClassifyUnknownFeedback
from navigator_msgs.srv import ObjectDBSingleQueryResponse, ObjectDBFullQueryResponse, ObjectDBSingleQuery, ObjectDBFullQuery
import actionlib
import rospy
import numpy as np
from nav_msgs.msg import Odometry
from rawgps_common.gps import ecef_from_latlongheight, enu_from_ecef
from visualization_msgs.msg import MarkerArray, Marker
from geometry_msgs.msg import Vector3, Pose
from navigator_tools import rosmsg_to_numpy, odometry_to_numpy
from txros import NodeHandle, util
from twisted.internet import defer, reactor

nh = None
class ObjectDatabase:

    def __init__(self):
        self.pose = None
        self.items = {}
        self.unknowns = []

    @util.cancellableInlineCallbacks
    def _init(self):
        self.nh = yield NodeHandle.from_argv("my_object_database")
        global nh
        nh = self.nh
    
        self.pub_object_found = yield self.nh.advertise('/database/object_found', PerceptionObject)
        self.pub_object_markers = yield self.nh.advertise('/database/objects_classified', MarkerArray)

        self.serv_single_query = yield self.nh.advertise_service('/database/single', ObjectDBSingleQuery, self.query_single)
        self.serv_full_query = yield self.nh.advertise_service('/database/full', ObjectDBFullQuery, self.query_full)

        self.sub_object_classification = yield self.nh.subscribe('/classifier/object', PerceptionObject, self.new_object)

        # rospy.init_node('find_unknown', anonymous=True)
        # self.act_classify_unknown = actionlib.SimpleActionServer('/database/find_unknown',
        #                                                          ClassifyUnknownAction,
        #                                                         execute_cb=self.classify_unknown,
        #                                                         auto_start=False)
        # self.act_classify_unknown.start()

        defer.returnValue(self)

    def classify_unknown(self):
        print "classifying unknown"

    def new_object(self, perceptionObject):
        p = perceptionObject
        if(p.name == 'unknown'):
            self.unknowns.append(perceptionObject)
            return 
        for i, unknown in enumerate(self.unknowns):
            if(p.id == unknown.id):
                del self.unknowns[i]
                break

        self.items[p.name] = p
        self.pub_object_found.publish(p)
        self.add_markers()

    def add_markers(self):
        marker_del = Marker()
        marker_del.action = 3 # This is DELETEALL
        marker_array = MarkerArray()
        marker_array.markers.append(marker_del)
        for item in self.items.values():
            marker = Marker()
            marker.header.stamp = nh.get_time()
            marker.header.seq = 1;
            marker.header.frame_id = "enu";     
            marker.id = item.id
            marker.pose.position = item.position
            marker.type = marker.TEXT_VIEW_FACING
            marker.action = marker.ADD
            marker.scale.x = 3.0
            marker.scale.y = 3.0
            marker.scale.z = 3.0
            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 0.0
            marker.color.a = 1.0
            marker.text = item.name
            marker_array.markers.append(marker)
        self.pub_object_markers.publish(marker_array)

        
    def query_single(self, req):
        a = req.name
        per = ObjectDBSingleQueryResponse()
        per.found = False
        if(a in self.items.keys()):
            per.object = self.items[a]
            per.found = True

        return per

    def query_full(self, req):
        per = ObjectDBFullQueryResponse()
        for item in self.items.values():
            per.objects.append(item)

        return per

       
@util.cancellableInlineCallbacks
def main():
    od = yield ObjectDatabase()._init() 

reactor.callWhenRunning(main)
reactor.run()