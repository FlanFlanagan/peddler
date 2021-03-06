"""
A simple truck model that passes material from one facility to another.
"""

import random
import numpy as np
import scipy as sp

from cyclus.agents import Facility
from cyclus import lib
import cyclus.typesystem as ts


class Truck(Facility):
    """
    A truck that transports material through the fuel cycle.
    """

    dest_commodity = ts.String(
        doc="The commodity that the truck carries",
        tooltip="Shipped Commodity",
        uilabel="Commodity"
    )

    source_commodity = ts.String(
        doc="The commodity that the truck carries",
        tooltip="Shipped Commodity",
        uilabel="Commodity"
    )

    contract = ts.PairDoubleMapIntDouble(
        doc="The contract quantity and recipe",
        tooltip="Contract quantity and recipe",
        uilabel="Contract",
        default=(0.0,{})
    )

    contractee = ts.Int(
        doc="The reactor that originates the contract with the truck (agentID)",
        tooltip="Reactor generating the contract",
        uilabel="Contractee",
        default=-1
    )

    total_trip_duration = ts.Int(
        doc="The reactor that originates the contract with the truck (agentID)",
        tooltip="Reactor generating the contract",
        uilabel="Contractee"
    )

    trip_time = ts.Int(
        doc="The reactor that originates the contract with the truck (agentID)",
        tooltip="Reactor generating the contract",
        uilabel="Contractee",
        default=-1
    )

    return_trip_time = ts.Int(
        doc="The reactor that originates the contract with the truck (agentID)",
        tooltip="Reactor generating the contract",
        uilabel="Contractee",
        default=-1
    )

    capacity = ts.Double(
        doc="The reactor that originates the contract with the truck (agentID)",
        tooltip="Reactor generating the contract",
        uilabel="Contractee",
    )

    inventory = ts.ResBufMaterialInv()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inventory.capacity = self.capacity
    
    def tock(self):
        #print("Truck: " + str(self.id) + " " + str(self.inventory.count))
        #print(self.return_trip_time, self.trip_time, self.total_trip_duration)
        if self.return_trip_time >= 0:
            self.return_trip_time += 1
        if self.return_trip_time == self.total_trip_duration:
            self.return_trip_time = -1
            return
        elif self.trip_time >= 0 and self.trip_time < self.total_trip_duration:
            self.trip_time += 1

    def get_material_requests(self):
        if self.return_trip_time >= 0:
            return []
        if self.contractee > -1 and self.inventory.count == 0:
            #requestfuel
            target_a = ts.Material.create_untracked(self.contract[0], self.contract[1])
            commods = {self.source_commodity: target_a}
            port = {"commodities": commods, "constraints": self.capacity}
            #print(str(self.id) + " is attempting to pick up fresh fuel")
            return [port]
        else:
            return []

    def get_material_bids(self, requests):
        if self.return_trip_time >= 0:
            return
        ports = []
        if self.dest_commodity not in requests and self.dest_commodity+"-contract" not in requests:
            return
        if self.contractee == -1 and self.inventory.count == 0:
            #print(str(self.id) + " is accepting contracts")
            #offercontract
            if self.dest_commodity+"-contract" in requests:
                reqs = requests[self.dest_commodity+"-contract"]
                bids = list(reqs)
                ports.append({"bids": bids, "constraints": self.capacity})
                return ports
        elif self.contractee > -1 and self.inventory.count > 0 and self.trip_time == self.total_trip_duration:
            #offerfuel
            bid = ""
            reqs = requests[self.dest_commodity]
            for req in reqs:
                if req.requester.id == self.contractee:
                    bid = req
                    break
            bids = [bid]
            ports.append({"bids": bids, "constraints": self.capacity})
            return ports
        else:
            return ports

    def get_material_trades(self, trades):
        responses = {}
        if self.return_trip_time >= 0:
            return responses
        if self.contractee == -1 and self.inventory.count == 0:
            #offercontract
            for trade in trades:
                self.contract = (trade.amt, trade.request.target.comp())
                self.contractee = trade.request.requester.id
                #print(str(self.id) + " is accepting a contract from " + str(self.contractee))
        elif self.contractee > -1 and self.inventory.count > 0 and self.trip_time == self.total_trip_duration:
            #offerfuel
            for trade in trades:
                mat = self.inventory.pop()
                responses[trade] = mat
            #print(str(self.id) + " is dropping off fuel at " + str(self.contractee))
            self.return_trip_time = 0
            self.contract = (-1, {})
            self.contractee = -1
        return responses

    def accept_material_trades(self, responses):
        if self.return_trip_time >= 0:
            return
        for mat in responses.values():
            self.inventory.push(mat)
            self.trip_time = 0
            #print(str(self.id) + " taking a load of fuel to " + str(self.contractee))
