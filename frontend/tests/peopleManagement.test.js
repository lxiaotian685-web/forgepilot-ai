import test from "node:test";
import assert from "node:assert/strict";
import { changePersonStatus, filterPeople, updatePerson } from "../src/services/peopleManagement.js";
const people = [{ id:"1", code:"EMP-01", name:"张工", role:"维修技师", team:"机械一班", status:"在岗", openOrders:2 }, { id:"2", code:"EMP-02", name:"王强", role:"诊断工程师", team:"可靠性组", status:"停用", openOrders:0 }];
test("filters people by role status team and query",()=>assert.deepEqual(filterPeople(people,{role:"维修技师",query:"张"}).map(p=>p.id),["1"]));
test("validates and updates a person",()=>{ assert.equal(updatePerson(people,"1",{name:"张师傅",role:"维修主管",team:"机械一班"})[0].role,"维修主管"); assert.throws(()=>updatePerson(people,"1",{}),/不能为空/); });
test("requires reassignment before deactivation",()=>{ assert.throws(()=>changePersonStatus(people,"1","停用"),/接收人/); assert.equal(changePersonStatus(people,"1","停用","王强")[0].status,"停用"); });
