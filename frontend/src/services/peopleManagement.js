export function filterPeople(people, filters = {}) {
  const query = filters.query?.trim().toLowerCase();
  return people.filter((person) => (!filters.role || person.role === filters.role) && (!filters.status || person.status === filters.status) && (!filters.team || person.team === filters.team) && (!query || [person.name, person.code, person.role, person.team].some((v) => v.toLowerCase().includes(query))));
}

export function updatePerson(people, id, changes) {
  if (!changes.name?.trim() || !changes.role || !changes.team) throw new Error("姓名、岗位和班组不能为空");
  return people.map((person) => person.id === id ? { ...person, ...changes, name: changes.name.trim() } : person);
}

export function changePersonStatus(people, id, status, reassignTo = "") {
  const person = people.find((item) => item.id === id);
  if (!person) throw new Error("人员不存在");
  if (status === "停用" && person.openOrders > 0 && !reassignTo) throw new Error("该人员仍有未完成工单，请先选择任务接收人");
  return people.map((item) => item.id === id ? { ...item, status, openOrders: status === "停用" ? 0 : item.openOrders } : item);
}
