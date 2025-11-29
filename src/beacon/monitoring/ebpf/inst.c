// Last Modified at Nov 23, 2025

#include <linux/capability.h>
#include <linux/cred.h>
#include <linux/filter.h>
#include <linux/ipc_namespace.h>
#include <linux/pid_namespace.h>
#include <linux/sched.h>
#include <linux/seccomp.h>
#include <linux/types.h>
#include <linux/utsname.h>
#include <uapi/linux/prctl.h>
#include <uapi/linux/seccomp.h>

/* fs/mount.h */
struct mnt_namespace {
  atomic_t count;
  struct ns_common ns;
  struct mount *root;
  struct list_head list;
  struct user_namespace *user_ns;
  struct ucounts *ucounts;
  u64 seq;
  wait_queue_head_t poll;
  u64 event;
  unsigned int mounts;
  unsigned int pending_mounts;
};

struct namespace_t {
  u32 cgroup;
  u32 user;
  u32 uts;
  u32 ipc;
  u32 mnt;
  u32 pid;
  u32 net;
};

struct sys_and_cap_t {
  bool seccomp_flag;
  bool padding[7];
  u32 sys[24];
  u32 cap[2];
};

BPF_PERCPU_HASH(event, struct namespace_t, struct sys_and_cap_t, 16384);

static struct namespace_t get_ns() {
  struct namespace_t ns;
  struct task_struct *task = (struct task_struct *)bpf_get_current_task();
  ns.cgroup = task->nsproxy->cgroup_ns->ns.inum;
  ns.user = task->nsproxy->cgroup_ns->user_ns->ns.inum;
  ns.uts = task->nsproxy->uts_ns->ns.inum;
  ns.ipc = task->nsproxy->ipc_ns->ns.inum;
  ns.mnt = task->nsproxy->mnt_ns->ns.inum;
  ns.pid = task->nsproxy->pid_ns_for_children->ns.inum;
  ns.net = task->nsproxy->net_ns->ns.inum;
  return ns;
}

static __always_inline struct sys_and_cap_t *get_or_init() {
  struct namespace_t ns = get_ns();
  struct sys_and_cap_t *sys_and_cap = event.lookup(&ns);
  if (sys_and_cap)
    return sys_and_cap;
  struct sys_and_cap_t zero = {};
  event.update(&ns, &zero);
  return event.lookup(&ns);
}

// TODO: unshare?
// Capset

////////////////////////////////////////////////////////////////////////////////
// name: sys_enter_seccomp // ID: 440 // format: //
//    field:unsigned short common_type;                 offset:0;    size:2;
//    signed:0; // field:unsigned char common_flags;                 offset:2;
//    size:1;    signed:0; // field:unsigned char common_preempt_count;
//    offset:3;    size:1;    signed:0; // field:int common_pid; offset:4;
//    size:4;    signed:1; //
//                                                                               //
//    field:int __syscall_nr;                                     offset:8; //
//    size:4;    signed:1; // field:unsigned int op; offset:16; size:8; //
//    signed:0; // field:unsigned int flags; offset:24; size:8;    signed:0; //
//    field:void * uargs;                                             offset:32;
//    size:8;    signed:0; //
////////////////////////////////////////////////////////////////////////////////
TRACEPOINT_PROBE(syscalls, sys_enter_seccomp) {
  struct sys_and_cap_t *sys_and_cap = get_or_init();
  struct namespace_t ns = get_ns();
  if (!sys_and_cap)
    return 0; // Cannot be happen, logic for the verifier

  if ((args->op != SECCOMP_SET_MODE_FILTER) || (args->uargs == NULL))
    return 0;

  sys_and_cap->seccomp_flag = true;
  event.update(&ns, sys_and_cap);
  return 0;
}

////////////////////////////////////////////////////////////////////////////////
// name: sys_enter_prctl // ID: 200 // format: //
//    field:unsigned short common_type;                 offset:0;    size:2;
//    signed:0; // field:unsigned char common_flags;                 offset:2;
//    size:1;    signed:0; // field:unsigned char common_preempt_count;
//    offset:3;    size:1;    signed:0; // field:int common_pid; offset:4;
//    size:4;    signed:1; //
//    //
//    field:int __syscall_nr;                                     offset:8;
//    size:4;    signed:1; // field:int option; offset:16; size:8;    signed:0;
//    // field:unsigned long arg2;                                 offset:24;
//    size:8;    signed:0; // field:unsigned long arg3; offset:32; size:8;
//    signed:0; // field:unsigned long arg4; offset:40; size:8;    signed:0; //
//    field:unsigned long arg5;                                 offset:48;
//    size:8;    signed:0; //
////////////////////////////////////////////////////////////////////////////////
TRACEPOINT_PROBE(syscalls, sys_enter_prctl) {
  struct namespace_t ns = get_ns();
  struct sys_and_cap_t *sys_and_cap = event.lookup(&ns);
  if (!sys_and_cap)
    return 0; // Not interested in this namespace
  if (args->option != PR_SET_SECCOMP)
    return 0;
  sys_and_cap->seccomp_flag = true;
  event.update(&ns, sys_and_cap);
  return 0;
}

////////////////////////////////////////////////////////////////////////////////
// name: sys_enter // ID: 22 // format: //
//    field:unsigned short common_type;                 offset:0;    size:2;
//    signed:0; // field:unsigned char common_flags;                 offset:2;
//    size:1;    signed:0; // field:unsigned char common_preempt_count;
//    offset:3;    size:1;    signed:0; // field:int common_pid; offset:4;
//    size:4;    signed:1; //
//    //
//    field:long id; offset:8;    size:8;    signed:1; // field:unsigned long
//    args[6];                            offset:16; size:48; signed:0; //
////////////////////////////////////////////////////////////////////////////////
TRACEPOINT_PROBE(raw_syscalls, sys_enter) {
  struct namespace_t ns = get_ns();
  struct sys_and_cap_t *sys_and_cap = event.lookup(&ns);
  if (!sys_and_cap)
    return 0;
  if (!sys_and_cap->seccomp_flag)
    return 0;

  u32 quot = args->id >> 5; // args->id : long type
  if ((quot >= 0) && (quot < 24)) {
    //                if (sys_and_cap->sys[quot] & (1 << (args->id % 32)))
    //                return 0;
    sys_and_cap->sys[quot] |= 1 << (args->id % 32);
    event.update(&ns, sys_and_cap);
  }
  return 0;
}

int kprobe__cap_capable(struct pt_regs *ctx, const struct cred *cred,
                        struct user_namespace *targ_ns, int cap, int cap_opt) {
  struct namespace_t ns = get_ns();
  struct sys_and_cap_t *sys_and_cap = event.lookup(&ns);
  if (!sys_and_cap)
    return 0;

  if (cap < 0 || cap >= 64)
    return 0;

  u32 bit;
  u32 idx;

  if (cap < 32) {
    idx = 0;
    bit = 1u << cap;
  } else {
    idx = 1;
    bit = 1u << (cap - 32);
  }

  sys_and_cap->cap[idx] |= bit;
  event.update(&ns, sys_and_cap);
  return 0;
}
