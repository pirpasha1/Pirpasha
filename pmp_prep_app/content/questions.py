"""Original practice questions written for this project (label DEMO until SME review).

Nothing here is copied from PMI, the PMBOK Guide or commercial prep material.
Approach codes: P = predictive, A = agile, H = hybrid.
"""

KEYS = "ABCDEFG"
APPR = {"P": "PREDICTIVE", "A": "AGILE", "H": "HYBRID"}
QUESTIONS = []
CASES = []


def _base(qid, task, appr, stem, expl, tags, d, concept, case):
    return dict(id=qid, domain=task.split("-T")[0], taskId=task, approach=APPR[appr], stem=stem,
                explanation=expl, tags=list(tags), difficulty=d, concept=concept,
                **({"caseId": case} if case else {}))


def S(qid, task, appr, stem, opts, ans, expl, why=None, tags=("scenario",), d=2, concept="", case=None):
    q = _base(qid, task, appr, stem, expl, tags, d, concept, case)
    q.update(type="MCQ_SINGLE", options=[dict(key=KEYS[i], text=t) for i, t in enumerate(opts)], correct=[ans])
    if why:
        q["rationales"] = {KEYS[i]: w for i, w in enumerate(why) if w}
    QUESTIONS.append(q)


def M(qid, task, appr, stem, opts, ans, expl, why=None, tags=(), d=3, concept="", case=None):
    q = _base(qid, task, appr, stem, expl, tags, d, concept, case)
    q.update(type="MCQ_MULTI", options=[dict(key=KEYS[i], text=t) for i, t in enumerate(opts)],
             correct=list(ans), selectCount=len(ans))
    if why:
        q["rationales"] = {KEYS[i]: w for i, w in enumerate(why) if w}
    QUESTIONS.append(q)


def MATCH(qid, task, appr, stem, pairs, distractors=(), expl="", tags=(), d=2, concept="", case=None):
    """pairs: list of (left text, right text). Right column is sorted so position gives nothing away."""
    q = _base(qid, task, appr, stem, expl, tags, d, concept, case)
    rights = sorted({r for _, r in pairs} | set(distractors))
    rkey = {t: f"R{i+1}" for i, t in enumerate(rights)}
    q.update(type="MATCHING", left=[dict(key=f"L{i+1}", text=l) for i, (l, _) in enumerate(pairs)],
             right=[dict(key=rkey[t], text=t) for t in rights],
             pairs={f"L{i+1}": rkey[r] for i, (_, r) in enumerate(pairs)})
    QUESTIONS.append(q)


def ORDER(qid, task, appr, stem, items_in_order, expl, tags=(), d=2, concept="", case=None):
    q = _base(qid, task, appr, stem, expl, tags, d, concept, case)
    # Items are stored in a scrambled-but-deterministic authoring order; the app shuffles again.
    idx = list(range(len(items_in_order)))
    scrambled = idx[1::2] + idx[0::2]
    q.update(type="DRAG_ORDER", items=[dict(key=f"I{i+1}", text=items_in_order[i]) for i in scrambled],
             correct=[f"I{i+1}" for i in idx])
    QUESTIONS.append(q)


def CAT(qid, task, appr, stem, buckets, items, expl, tags=(), d=2, concept="", case=None):
    """items: list of (text, bucket index)."""
    q = _base(qid, task, appr, stem, expl, tags, d, concept, case)
    q.update(type="DRAG_CATEGORIZE", buckets=[dict(key=f"B{i+1}", text=b) for i, b in enumerate(buckets)],
             items=[dict(key=f"I{i+1}", text=t) for i, (t, _) in enumerate(items)],
             pairs={f"I{i+1}": f"B{b+1}" for i, (_, b) in enumerate(items)})
    QUESTIONS.append(q)


# ---------------------------------------------------------------- PEOPLE
S("P001", "PEOPLE-T1", "A",
  "A newly formed agile team is debating which features matter most, and each member argues from their own department's point of view. What should the project manager do first?",
  ["Ask the sponsor to rank the features and share the list", "Facilitate a session with the team and product owner to create a shared product vision",
   "Assign the most experienced developer to make feature decisions", "Start the first sprint and let priorities emerge from velocity"],
  "B", "A shared vision gives the team a common basis for decisions. Co-creating it with the product owner builds ownership and resolves departmental tunnel vision.",
  ["Imposing a ranking skips alignment; the team still lacks a shared 'why'.", None,
   "Delegating to one person bypasses collaboration and the product owner's role.", "Starting without direction wastes effort; velocity does not set priorities."],
  concept="Product vision")

S("P002", "PEOPLE-T2", "P",
  "Two functional leads repeatedly argue about test-environment time during status meetings, and the meetings now overrun. What is the BEST action for the project manager?",
  ["Meet both leads together to understand their needs and agree a shared booking approach", "Escalate the issue to their functional managers",
   "Give priority to the lead whose work is on the critical path", "Remove the topic from the status meeting agenda"],
  "A", "Collaborating / problem-solving addresses the root cause and builds commitment. It is the preferred first approach.",
  [None, "Escalation is premature before the PM tries to resolve it.", "Forcing a decision may be needed later but ignores the other lead's needs.", "Withdrawing avoids the conflict without solving it."],
  concept="Conflict resolution techniques")

S("P003", "PEOPLE-T2", "A",
  "During a retrospective, one developer becomes visibly upset after a teammate criticizes his code in front of everyone. What should the scrum master do?",
  ["Ask the developer to stay calm and continue the retrospective", "End the retrospective early and report the incident to HR",
   "Pause, remind the team of the working agreement on respectful feedback, and follow up privately with both people", "Ignore it, as conflict is healthy in agile teams"],
  "C", "Psychological safety is essential. Using the team's own working agreement and following up privately addresses the behaviour without humiliating anyone.",
  ["Dismissing emotions damages psychological safety.", "HR escalation is disproportionate for a first incident.", None, "Healthy conflict is about ideas; this has become personal."],
  tags=("situational",), concept="Team charter, psychological safety")

S("P004", "PEOPLE-T3", "A",
  "A team member has been late with their tasks for three sprints and seems disengaged in meetings. What should the project manager do first?",
  ["Raise the issue in the daily stand-up so the team can help", "Meet privately with the team member to understand what is happening",
   "Ask the functional manager to replace the team member", "Reassign their stories to other team members"],
  "B", "Leaders give corrective attention privately and start by understanding the cause, which might be personal, skill-related or a blocker.",
  ["Public discussion can embarrass the person.", None, "Replacement is premature without understanding the cause.", "Reassigning treats the symptom only."],
  tags=("situational",), concept="Emotional intelligence, servant leadership")

S("P005", "PEOPLE-T3", "H",
  "Your organization has started allowing generative-AI assistants for drafting project documents. A team member pasted confidential client requirements into a public AI tool. What should you do FIRST?",
  ["Ban all AI tools for the team immediately", "Report the incident according to the organization's data-protection procedure and contain the exposure",
   "Ask the team member to delete their chat history and say nothing", "Add an item to the lessons-learned register"],
  "B", "Data exposure is a compliance and security incident. It must be reported and contained using the organization's procedures. Team norms for responsible AI use can follow.",
  ["A blanket ban may be considered later, but it does not address the exposure.", None, "Concealing the incident breaches policy and ethics.", "Lessons learned are useful, but not first."],
  tags=("situational", "ai"), d=3, concept="Responsible AI use")

M("P006", "PEOPLE-T3", "A",
  "Which TWO actions best demonstrate servant leadership by a project manager on an agile team?",
  ["Removing an impediment the team cannot resolve themselves", "Assigning daily tasks to each developer",
   "Shielding the team from mid-sprint requests from outside stakeholders", "Approving every technical design decision personally", "Reporting each team member's velocity individually"],
  ["A", "C"], "Servant leaders enable the team by removing impediments and protecting focus. Task assignment, approval gates and individual metrics undermine self-organization.",
  ["Correct: removing impediments is a core servant-leader duty.", "Assigning tasks undermines self-organization.", "Correct: protecting the team's focus enables delivery.",
   "Central approval creates a bottleneck.", "Individual velocity encourages local optimization and gaming."], concept="Servant leadership")

S("P007", "PEOPLE-T4", "P",
  "Three months into a construction project, the project manager learns that a local residents' association has concerns about noise. The association is not in the stakeholder register. What should the project manager do NEXT?",
  ["Add the association to the stakeholder register and analyze its interest and influence", "Send the association the project's noise permits",
   "Ask the sponsor to deal with external groups", "Continue as planned because the permits are already approved"],
  "A", "Stakeholder identification is continuous. A newly found stakeholder is first recorded and analyzed so engagement can be planned.",
  [None, "Sending documents without analysis may not address the concern.", "The PM owns stakeholder engagement.", "Ignoring an influential group risks delays."],
  concept="Stakeholder register")

S("P008", "PEOPLE-T4", "H",
  "A key business user rarely attends sprint reviews, and features delivered for her department have had low adoption. What is the BEST approach?",
  ["Escalate her absence to the sponsor", "Meet her to understand her constraints and agree a more convenient way to involve her in feedback",
   "Stop building features for her department", "Ask the product owner to accept the features on her behalf"],
  "B", "Engagement must suit the stakeholder. Understanding her constraints and adapting the format (short demos, async video, a delegate) moves her from neutral to supportive.",
  ["Escalation before trying to engage damages the relationship.", None, "Abandoning features ignores real business needs.", "Acceptance without user input continues the adoption problem."],
  concept="Engagement assessment matrix")

S("P009", "PEOPLE-T5", "P",
  "Marketing requires a product launch in June, but the compliance team states that mandatory controls cannot be ready until August. Both are powerful stakeholders. What should the project manager do?",
  ["Proceed with the June launch and add the controls afterwards", "Facilitate a joint meeting to explore options against business objectives and take the trade-off to the sponsor",
   "Side with compliance because regulation always wins", "Ask each stakeholder to submit a change request"],
  "B", "Alignment means bringing conflicting stakeholders together around objectives and finding options. For example, a limited pilot could launch while the controls are completed. Genuine trade-offs go to the sponsor.",
  ["Launching without mandatory controls breaches compliance.", None, "Compliance must be met, but other options may satisfy both groups.", "Change requests do not resolve the underlying conflict."],
  d=3, concept="Aligning expectations")

S("P010", "PEOPLE-T6", "A",
  "During a sprint review, the sponsor says she expected a feature that was never in the product backlog. What should the project manager do?",
  ["Promise to add it in the next sprint", "Explain that the feature is out of scope and move on",
   "Work with the product owner to discuss the need and, if valuable, add it to the backlog for prioritization", "Ask the team to work overtime to include it in this sprint"],
  "C", "In agile, new needs go into the product backlog, where the product owner prioritizes them against other value. This respects the sponsor's need without disrupting the sprint.",
  ["The PM cannot promise; prioritization belongs to the product owner.", "Dismissing the sponsor damages engagement.", None, "Overtime and mid-sprint scope changes are unsustainable."],
  concept="Product backlog")

S("P011", "PEOPLE-T7", "H",
  "A senior engineer who is the only expert on a legacy interface will leave the project in four weeks. What should the project manager do?",
  ["Ask the engineer to write complete documentation before leaving", "Arrange pairing and shadowing with a successor, supported by key documentation",
   "Request that HR extend the engineer's assignment", "Add a risk to the register and accept it"],
  "B", "Tacit knowledge transfers best through people: pairing and shadowing. Documentation supports it but cannot capture judgment alone.",
  ["Documentation alone misses tacit knowledge.", None, "Extension may not be possible and only delays the problem.", "Acceptance is passive when a mitigation is available."],
  concept="Tacit vs explicit knowledge")

S("P012", "PEOPLE-T8", "P",
  "A project team grows from 6 to 10 members. How many additional communication channels does this create?",
  ["4", "15", "30", "45"], "C", "Channels = n(n−1)/2. For 6 people: 15. For 10 people: 45. Additional channels = 45 − 15 = 30.",
  ["4 is just the extra people.", "15 is the original number of channels.", None, "45 is the new total, not the increase."],
  tags=("calculation",), concept="Communication channels")

S("P013", "PEOPLE-T8", "H",
  "Team members in three countries complain that they learn about decisions late. Meetings are held in the head office's time zone. What should the project manager do FIRST?",
  ["Review the communications management plan with the team and adjust channels, timing and a shared decision log", "Require everyone to attend all meetings regardless of local time",
   "Send a weekly summary email to the whole team", "Escalate the time-zone problem to the PMO"],
  "A", "Revisit the communications plan with the people affected. Use a mix of pull (decision log), push and interactive methods, and set fair meeting times.",
  [None, "This ignores wellbeing and fairness.", "Summaries help, but alone they may not fix the timing of decisions.", "The PM can resolve this within their authority."],
  concept="Communications management plan")

MATCH("P014", "PEOPLE-T2", "P", "Match each conflict-resolution technique to its description.",
      [("Collaborate / problem-solve", "Incorporate multiple viewpoints to reach consensus"),
       ("Compromise", "Each party gives up something to reach a partial solution"),
       ("Smooth / accommodate", "Emphasize areas of agreement over differences"),
       ("Force / direct", "Impose one viewpoint, often for urgent or safety issues")],
      distractors=("Escalate every conflict to the sponsor",),
      expl="Collaborating gives the most durable solution. Compromise is lose-lose but workable. Smoothing preserves relationships temporarily. Forcing suits emergencies.",
      concept="Conflict resolution")

CAT("P015", "PEOPLE-T4", "P", "Place each stakeholder in the most appropriate power/interest grid quadrant.",
    ["Manage closely", "Keep satisfied", "Keep informed", "Monitor"],
    [("Project sponsor who approves funding and attends every steering meeting", 0),
     ("CFO who signs off budget but rarely follows project details", 1),
     ("End users eager for the new system but with no decision authority", 2),
     ("Building facilities staff who are minimally affected", 3)],
    "High power and high interest: manage closely. High power and low interest: keep satisfied. Low power and high interest: keep informed. Low on both: monitor.",
    concept="Power/interest grid")

ORDER("P016", "PEOPLE-T4", "P", "Arrange these stakeholder engagement activities in the order they are normally performed.",
      ["Identify stakeholders", "Analyze power, interest and attitudes", "Plan engagement strategies",
       "Carry out engagement actions", "Monitor engagement and adjust"],
      "Engagement follows identify → analyze → plan → engage → monitor, and repeats as new stakeholders appear.", concept="Stakeholder engagement")

S("P017", "PEOPLE-T1", "P",
  "The project charter has been approved, but team members describe the project's purpose very differently. What should the project manager do?",
  ["Email the charter to the team again", "Hold a kickoff workshop to walk through the business case, objectives and success criteria, and invite questions",
   "Ask the sponsor to issue a memo to the team", "Proceed; purposes become clear during execution"],
  "B", "Interactive sessions build shared understanding. A document alone rarely creates a common vision.",
  ["Pushing the document again is unlikely to change understanding.", None, "A memo is one-way communication.", "Misunderstanding now causes rework later."],
  concept="Kickoff meeting")

S("P018", "PEOPLE-T6", "P",
  "Testing shows the project will miss the milestone the customer expects next month. The customer has not been told. What should the project manager do?",
  ["Wait until the testing results are final", "Inform the customer promptly with the impact, cause and recovery options",
   "Ask the team to compress testing to protect the date", "Report the milestone as 'at risk' only on the internal dashboard"],
  "B", "Transparency and early communication of bad news maintain trust and give stakeholders time to decide.",
  ["Delay reduces the options available.", None, "Compressing testing creates quality risk.", "Hiding it from the customer erodes trust."],
  tags=("situational",), concept="Managing expectations")

S("P019", "PEOPLE-T3", "P",
  "A highly skilled but new team member is unsure about a complex task. Using situational leadership, which style is MOST appropriate?",
  ["Delegating", "Supporting", "Coaching", "Directing"], "C",
  "Someone with some competence and variable confidence benefits from coaching: high direction plus high support.",
  ["Delegating suits high competence and high commitment.", "Supporting suits capable people with low confidence on familiar tasks.", None, "Directing suits enthusiastic beginners with low skill."],
  d=3, concept="Situational leadership")

M("P020", "PEOPLE-T7", "A", "Which THREE practices help transfer knowledge within and beyond an agile team?",
  ["Pair programming", "Communities of practice", "Keeping the lessons-learned register private to the PM", "Recording short demo videos for support staff", "Assigning each component to one specialist only"],
  ["A", "B", "D"], "Pairing, communities of practice and accessible recordings spread knowledge. Private registers and single specialists create knowledge silos.",
  concept="Knowledge transfer")

S("P021", "PEOPLE-T5", "A",
  "Two business units want contradictory features in the next release. The product owner asks the project manager for help. What should the project manager do?",
  ["Decide which feature is more valuable", "Facilitate a prioritization workshop with both units using agreed value criteria, so the product owner can decide",
   "Build both features with half the effort each", "Escalate to the sponsor immediately"],
  "B", "The product owner owns prioritization. The PM facilitates by bringing the stakeholders together and making value transparent.",
  ["Prioritization is the product owner's call.", None, "Splitting effort usually delivers neither well.", "Escalation comes after facilitation fails."],
  concept="Value-based prioritization")

S("P022", "PEOPLE-T8", "A", "Which artifact is the BEST example of an information radiator?",
  ["The communications management plan", "A Kanban board displayed where the team and stakeholders can see it", "A monthly status report emailed to sponsors", "The stakeholder register"],
  "B", "Information radiators are highly visible, current displays of progress, such as Kanban boards and burndown charts.",
  ["A plan is not a live display.", None, "Email is push communication.", "The register is not a progress display and may hold sensitive data."],
  tags=(), d=1, concept="Information radiator")

S("P023", "PEOPLE-T1", "H",
  "Mid-project, the organization announces a sustainability commitment to cut emissions by 30%. How should the project manager handle the project vision?",
  ["Ignore it, as the charter was already approved", "Work with the sponsor to assess the impact and, if needed, update the vision and success criteria to include sustainability outcomes",
   "Add a sustainability slide to the next status report", "Wait for the next project to adopt it"],
  "B", "The vision must stay aligned with organizational strategy. The July 2026 outline emphasizes sustainability and value. Updating the vision is done openly, with the sponsor.",
  ["Strategy changes can invalidate the charter's assumptions.", None, "A slide doesn't change direction.", "Waiting misses alignment with strategy."],
  tags=("scenario", "sustainability"), d=3, concept="Vision and strategic alignment")

S("P024", "PEOPLE-T2", "P",
  "A safety inspector and the site supervisor disagree about whether scaffolding can be used today. Work is due to start in one hour. Which conflict approach is most appropriate?",
  ["Compromise: use the scaffolding for half the day", "Force: follow the safety inspector's decision until the issue is resolved",
   "Smooth: emphasize shared goals and proceed", "Withdraw: let them sort it out"],
  "B", "Safety issues justify a directive (forcing) approach. Safety always takes precedence; the underlying disagreement can be resolved afterwards.",
  ["Partial use is still unsafe.", None, "Proceeding ignores the safety concern.", "Withdrawing leaves risk unmanaged."],
  tags=("situational",), concept="Forcing in emergencies")

# ---------------------------------------------------------------- PROCESS
S("R001", "PROCESS-T1", "H",
  "A project will build a regulated medical device with a companion mobile app. Device requirements are fixed by regulation; app features depend on user feedback. Which delivery approach is MOST appropriate?",
  ["Predictive for the whole project", "Agile for the whole project", "Hybrid: predictive for the device, iterative and incremental for the app", "Wait until all app requirements are known"],
  "C", "Hybrid combines approaches based on each component's uncertainty and constraints.",
  ["Predictive suits the device but slows app learning.", "Agile alone may conflict with regulatory documentation and gates.", None, "Waiting delays value and learning."],
  d=2, concept="Choosing the development approach")

S("R002", "PROCESS-T1", "P", "Which items make up the performance measurement baseline?",
  ["Scope, schedule and cost baselines", "Scope baseline, risk register and quality plan", "Cost baseline and management reserve", "Project charter and project management plan"],
  "A", "The performance measurement baseline integrates the scope, schedule and cost baselines. Management reserve is not part of it.",
  [None, "The risk register and quality plan are not baselines.", "Management reserve sits outside the baseline.", "The charter authorizes; it is not a baseline."],
  tags=(), d=1, concept="Performance measurement baseline")

S("R003", "PROCESS-T2", "P",
  "A developer adds an extra dashboard widget that the customer did not request, believing it will please them. This is an example of:",
  ["Scope creep", "Gold plating", "Progressive elaboration", "Value engineering"], "B",
  "Gold plating means adding features beyond requirements without a request. It adds risk and cost and is discouraged.",
  ["Scope creep is uncontrolled change, usually from stakeholders.", None, "Progressive elaboration is adding detail as information emerges.", "Value engineering seeks the same function at lower cost."],
  tags=(), d=1, concept="Gold plating")

S("R004", "PROCESS-T2", "P",
  "The customer inspected the completed deliverables and formally signed acceptance. Which process does this represent?",
  ["Control quality", "Validate scope", "Close project", "Control scope"], "B",
  "Validate scope is formal customer acceptance of deliverables. Control quality (verification of correctness) normally happens before it.",
  ["Control quality checks correctness internally.", None, "Closing comes after acceptance of all deliverables.", "Control scope monitors scope and changes."],
  tags=(), d=1, concept="Validate scope vs control quality")

ORDER("R005", "PROCESS-T2", "P", "Arrange these scope management activities in the typical predictive order.",
      ["Collect requirements", "Define scope (scope statement)", "Create the WBS", "Validate scope with the customer", "Control scope throughout the project"],
      "Predictive scope work moves from requirements to scope statement, WBS decomposition, then ongoing validation and control.", concept="Scope management")

S("R006", "PROCESS-T3", "A",
  "Stakeholders want all twelve planned reports delivered together at the end of the project. Usage of the current reporting system is unknown. What should the project manager recommend?",
  ["Deliver all twelve reports together as requested", "Release the two highest-value reports first, measure usage and adjust the backlog",
   "Ask the team to estimate all twelve in detail first", "Cancel the reporting scope"],
  "B", "Value-based delivery releases the highest-value items early to gain feedback and value sooner. This often reveals unneeded scope.",
  ["Big-bang delivery delays value and feedback.", None, "Detailed upfront estimates add little value under uncertainty.", "Cancelling ignores a legitimate need."],
  concept="Incremental value delivery")

M("R007", "PROCESS-T3", "H", "Which TWO measures best indicate that a project is delivering business value rather than just outputs?",
  ["Number of features completed", "Increase in customer adoption rate", "Lines of code written", "Reduction in processing time for the target business process", "Hours logged by the team"],
  ["B", "D"], "Outcome measures such as adoption and process improvement show value. Output counts do not.",
  concept="Outcomes vs outputs")

S("R008", "PROCESS-T4", "P",
  "A critical specialist is over-allocated across two activities in the same week, and both activities have float. Which technique should be used FIRST?",
  ["Resource levelling", "Resource smoothing", "Crashing", "Fast tracking"], "B",
  "Resource smoothing reschedules within available float, so the critical path is not affected. Use it before levelling, which may extend the project.",
  ["Levelling can change the end date; use it if smoothing is insufficient.", None, "Crashing adds resources to shorten duration.", "Fast tracking overlaps activities to save time."],
  d=3, concept="Resource smoothing vs levelling")

S("R009", "PROCESS-T4", "P",
  "A functional manager reassigns a key team member to another project without notice. What should the project manager do FIRST?",
  ["Escalate to the sponsor", "Meet the functional manager to understand the reason and negotiate a solution",
   "Hire a contractor immediately", "Update the schedule to show the delay"],
  "B", "In a matrix organization the PM negotiates resources with functional managers first; escalation comes later if needed.",
  ["Escalation before negotiation harms relationships.", None, "Hiring may be unnecessary and is not first.", "Re-planning happens after the situation is understood."],
  concept="Negotiating resources")

S("R010", "PROCESS-T5", "P",
  "The scope of work for a vendor is well defined and stable, and the buyer wants to minimize its own cost risk. Which contract type is MOST appropriate?",
  ["Cost plus fixed fee", "Time and materials", "Firm fixed price", "Cost plus award fee"], "C",
  "With a clear, stable scope, firm fixed price places most cost risk on the seller.",
  ["Cost-reimbursable contracts put risk on the buyer.", "T&M suits small or undefined work.", None, "Award-fee contracts are cost-reimbursable."],
  tags=(), d=1, concept="Contract types")

S("R011", "PROCESS-T5", "P",
  "A seller claims additional payment because, it says, the buyer changed requirements. The buyer disagrees. What is the PREFERRED way to resolve this?",
  ["Take the seller to court", "Negotiate according to the contract's claims administration process", "Withhold all payments until the seller drops the claim", "Terminate the contract"],
  "B", "Contested changes (claims) should be settled by negotiation following the contract's terms. Alternative dispute resolution or litigation are later options.",
  ["Litigation is a last resort.", None, "Withholding payment may breach the contract.", "Termination is extreme and costly."],
  concept="Claims administration")

MATCH("R012", "PROCESS-T5", "P", "Match each procurement document to its purpose.",
      [("RFI", "Gather information about seller capabilities"), ("RFQ", "Request price quotes for well-defined items"),
       ("RFP", "Request detailed solution proposals"), ("SOW", "Describe the work to be performed")],
      distractors=("Record contested changes",),
      expl="RFI gathers information, RFQ requests prices, RFP requests proposals, and the SOW describes the work.", concept="Procurement documents")

S("R013", "PROCESS-T6", "P",
  "BAC = 200,000. EV = 80,000. AC = 100,000. PV = 90,000. What is the cost performance index (CPI)?",
  ["0.80", "0.89", "1.13", "1.25"], "A", "CPI = EV / AC = 80,000 / 100,000 = 0.80. The project is over budget.",
  [None, "0.89 is SPI (EV/PV).", "1.13 is PV/EV.", "1.25 is AC/EV."], tags=("calculation",), concept="Earned value")

S("R014", "PROCESS-T6", "P",
  "Using the same data (BAC 200,000, EV 80,000, AC 100,000), what is the estimate at completion if current cost performance continues?",
  ["220,000", "250,000", "180,000", "200,000"], "B", "EAC = BAC / CPI = 200,000 / 0.8 = 250,000.",
  ["220,000 is AC + (BAC − EV).", None, "Not a valid formula result.", "That is the BAC, which assumes no variance."], tags=("calculation",), d=3, concept="EAC")

S("R015", "PROCESS-T6", "P",
  "Where is the contingency reserve for identified risks held?",
  ["Outside the cost baseline, controlled by management", "Inside the cost baseline", "In the procurement budget", "In the management reserve"],
  "B", "Contingency reserves (for known-unknowns) are part of the cost baseline. Management reserve (unknown-unknowns) is outside it.",
  ["That describes management reserve.", None, "Not a standard reserve location.", "Management reserve is for unknown-unknowns."], tags=(), concept="Reserves")

S("R016", "PROCESS-T6", "P",
  "An activity has optimistic 6, most likely 9 and pessimistic 18 days. What is the PERT (beta) estimate?",
  ["9 days", "10 days", "11 days", "12 days"], "B", "(O + 4M + P) / 6 = (6 + 36 + 18) / 6 = 10 days.",
  ["9 is the most likely value only.", None, "11 is the triangular average.", "Not a valid result."], tags=("calculation",), concept="Three-point estimating")

S("R017", "PROCESS-T7", "P",
  "A control chart shows seven consecutive measurements above the mean, all within the control limits. What should the project manager conclude?",
  ["The process is in control; no action is needed", "The process may be out of control and should be investigated",
   "The control limits should be widened", "The specification limits have been exceeded"],
  "B", "The 'rule of seven': seven consecutive points on one side of the mean suggests a non-random pattern that needs investigation.",
  ["Points within limits can still show a non-random trend.", None, "Changing limits hides the signal.", "No information about specification limits is given."],
  tags=(), concept="Control charts")

CAT("R018", "PROCESS-T7", "P", "Classify each cost as a cost of conformance or a cost of non-conformance.",
    ["Cost of conformance", "Cost of non-conformance"],
    [("Team training", 0), ("Product inspections", 0), ("Rework of defective units", 1), ("Warranty claims", 1), ("Test equipment", 0), ("Lost business from poor reviews", 1)],
    "Prevention (training) and appraisal (inspection, testing) are conformance costs. Internal and external failures (rework, warranty, lost business) are non-conformance costs.",
    concept="Cost of quality")

S("R019", "PROCESS-T7", "A",
  "A team keeps finding defects during the sprint review that should have been caught earlier. What is the BEST way to prevent this?",
  ["Add a separate testing sprint after every two development sprints", "Strengthen the definition of done to include automated tests and peer review",
   "Ask the product owner to stop accepting stories", "Extend the sprint by a week"],
  "B", "Agile builds quality in. A stronger definition of done prevents defects instead of finding them late.",
  ["Separate test sprints delay feedback (a 'mini waterfall').", None, "Withholding acceptance does not fix the cause.", "Longer sprints do not fix the process."],
  concept="Definition of done")

S("R020", "PROCESS-T8", "P",
  "The project is three weeks behind schedule. The sponsor will not approve more budget but accepts some additional risk. Which compression technique fits BEST?",
  ["Crashing", "Fast tracking", "Resource levelling", "Reducing scope without approval"], "B",
  "Fast tracking overlaps activities. It adds risk rather than cost, which matches the sponsor's constraints.",
  ["Crashing adds cost.", None, "Levelling usually lengthens the schedule.", "Scope changes need approval."], concept="Schedule compression")

S("R021", "PROCESS-T8", "P",
  "Activity A (4 days) precedes B (6 days) and C (3 days). B and C both precede D (2 days). What is the critical path duration?",
  ["9 days", "12 days", "15 days", "13 days"], "B", "Paths: A-B-D = 4 + 6 + 2 = 12; A-C-D = 4 + 3 + 2 = 9. The longest is 12 days.",
  ["9 is the shorter path.", None, "15 is the sum of all activities.", "Not a valid path."], tags=("calculation",), concept="Critical path")

S("R022", "PROCESS-T8", "A",
  "An agile team's velocity over the last four sprints was 30, 34, 28 and 32 points. 192 points remain in the release, and the team only releases at sprint ends. How many more sprints should the forecast show?",
  ["5", "6", "7", "8"], "C", "Average velocity = 31 points. 192 / 31 ≈ 6.2 sprints. Because work completes only at sprint boundaries, the forecast is 7 sprints. Present it as a range (6–7) to stakeholders.",
  ["5 sprints would need about 38 points per sprint.", "6 sprints delivers only about 186 points, short of 192.", None, "8 is overly pessimistic given stable velocity."], tags=("calculation",), d=3, concept="Velocity forecasting")

S("R023", "PROCESS-T9", "A",
  "A cumulative flow diagram shows the 'In test' band widening every week while 'Done' grows slowly. What does this indicate?",
  ["The team is highly productive", "A bottleneck in testing", "Scope is decreasing", "The backlog needs more stories"],
  "B", "A widening band means work is accumulating in that state: a bottleneck. Limiting WIP and swarming on testing are typical responses.",
  ["Accumulating WIP is not productivity.", None, "Scope is shown by the total height.", "The backlog is not the constraint."], concept="Cumulative flow diagram")

S("R024", "PROCESS-T9", "P",
  "Status reports show green for six months, but the integration test reveals major defects. The sponsor asks why. What should the project manager do going forward?",
  ["Keep reporting green to avoid alarming the sponsor", "Base status on objective measures such as test results and earned value, and report risks transparently",
   "Stop issuing status reports", "Blame the test team for late testing"],
  "B", "Honest, metric-based reporting prevents 'watermelon' status and supports timely decisions.",
  ["This repeats the problem.", None, "Stakeholders need status information.", "Blame does not fix reporting."], tags=("situational",), concept="Status reporting")

S("R025", "PROCESS-T10", "P",
  "The project's final deliverable is accepted. One vendor contract still has an open punch-list item. What should the project manager do before closing the project?",
  ["Close the project and handle the vendor later", "Complete procurement closure by resolving the open item and confirming contract completion",
   "Transfer the open item to operations", "Archive the contract file"],
  "B", "Procurements must be closed (all work complete and claims settled) before the project is closed.",
  ["Leaving contracts open creates liability.", None, "Contract obligations remain with the project.", "Archiving doesn't resolve the open item."], concept="Closing procurements")

S("R026", "PROCESS-T10", "H",
  "The sponsor terminates the project because of a strategic merger. What should the project manager do?",
  ["Release the team immediately and stop all activity", "Follow closure procedures: document status, close contracts, archive work, capture lessons learned and release resources",
   "Keep working quietly in case the decision changes", "Ask the team to finish their current tasks"],
  "B", "Terminated projects still go through closure to protect the organization and preserve knowledge.",
  ["Stopping abruptly loses knowledge and leaves obligations open.", None, "Continuing defies the governance decision.", "Further work is not authorized."], concept="Project termination")

M("R027", "PROCESS-T10", "P", "Which THREE activities belong to project closure?",
  ["Obtain final acceptance of deliverables", "Create the WBS", "Finalize the lessons-learned register", "Transfer the product to operations", "Develop the project charter"],
  ["A", "C", "D"], "Closure confirms acceptance, finalizes lessons learned and transitions the product. The WBS and charter are created in planning and initiation.", concept="Closing")

S("R028", "PROCESS-T1", "A", "Which event formally marks the start of execution and aligns the team and stakeholders on the plan?",
  ["Sprint retrospective", "Kickoff meeting", "Phase gate review", "Lessons-learned session"], "B",
  "The kickoff meeting launches the project or a major phase and aligns everyone on objectives, roles and plans.",
  ["Retrospectives look back.", None, "Gates decide go/no-go.", "Lessons sessions capture learning."], tags=(), d=1, concept="Kickoff")

MATCH("R029", "PROCESS-T6", "P", "Match each earned value formula to what it calculates.",
      [("EV − AC", "Cost variance (CV)"), ("EV − PV", "Schedule variance (SV)"), ("EV / AC", "Cost performance index (CPI)"), ("BAC / CPI", "Estimate at completion (EAC)")],
      distractors=("To-complete performance index (TCPI)",),
      expl="CV = EV − AC; SV = EV − PV; CPI = EV / AC; EAC = BAC / CPI when current performance continues.", concept="Earned value")

S("R030", "PROCESS-T3", "A", "What is the main purpose of a minimum viable product (MVP)?",
  ["Deliver the full scope at the lowest cost", "Test a value hypothesis with the smallest useful release to gain feedback",
   "Satisfy contractual milestones", "Produce a prototype that will be thrown away"],
  "B", "An MVP tests assumptions about value with real users as early as possible.",
  ["MVP is not full scope.", None, "Milestones may differ from value hypotheses.", "An MVP is usable, not necessarily throwaway."], tags=(), d=1, concept="MVP")

ORDER("R031", "PROCESS-T6", "P", "Arrange the steps of building a project budget in order.",
      ["Estimate activity costs", "Aggregate to work-package and control-account costs", "Add contingency reserves to form the cost baseline", "Add management reserve to form the total budget"],
      "Costs roll up from activities to work packages and control accounts. Contingency makes the cost baseline; management reserve completes the project budget.", concept="Cost aggregation")

S("R032", "PROCESS-T4", "A",
  "An agile organization wants to maximize team performance on a long-running product. Which staffing approach is BEST?",
  ["Reassign developers every sprint based on availability", "Keep a stable, dedicated, cross-functional team",
   "Use specialists from a central pool per task", "Rotate the product owner weekly"],
  "B", "Stable, dedicated, cross-functional teams build trust, shared knowledge and predictable velocity.",
  ["Frequent reassignment destroys team learning.", None, "Pooling creates handoffs and waits.", "Product ownership needs continuity."], tags=(), concept="Team structure")

# ---------------------------------------------------------------- BUSINESS ENVIRONMENT
S("B001", "BUSINESS_ENV-T1", "P",
  "A decision about a 500,000 vendor contract is above the project manager's authority. Two stakeholders are pressing for a quick decision. What should the project manager do?",
  ["Make the decision to keep the project moving", "Prepare options and impacts, and take the decision to the steering committee per the governance framework",
   "Let the two stakeholders decide between themselves", "Delay the decision until the next phase"],
  "B", "Governance defines decision rights. The PM supports the decision with analysis and follows the escalation path.",
  ["Exceeding authority breaches governance.", None, "Stakeholders lack the formal authority.", "Delay may harm the project."], concept="Decision rights")

S("B002", "BUSINESS_ENV-T1", "P", "In which organizational structure does the project manager typically have the MOST authority?",
  ["Functional", "Weak matrix", "Balanced matrix", "Projectized"], "D",
  "In projectized organizations the PM controls budget and resources. Authority is lowest in functional organizations.",
  ["Functional: authority sits with functional managers.", "Weak matrix: the PM is more of a coordinator.", "Balanced: authority is shared.", None], tags=(), d=1, concept="Organizational structures")

MATCH("B003", "BUSINESS_ENV-T1", "H", "Match each PMO type to its level of control.",
      [("Supportive", "Provides templates and training; low control"), ("Controlling", "Requires compliance with frameworks; moderate control"),
       ("Directive", "Directly manages projects; high control")],
      distractors=("Approves individual sprint backlogs",),
      expl="PMO types range from supportive (low control) to controlling (moderate) to directive (high).", concept="PMO types")

S("B004", "BUSINESS_ENV-T2", "H",
  "Midway through a CRM rollout, a new data-protection regulation takes effect that requires explicit consent tracking. What should the project manager do FIRST?",
  ["Ignore it until the next release", "Engage the compliance or privacy officer to assess the impact and requirements",
   "Add consent tracking directly to the current sprint", "Ask the vendor to absorb the change"],
  "B", "First understand the regulatory requirements with experts, then plan the change (backlog, change control, risk updates).",
  ["Non-compliance is not optional.", None, "Acting before understanding may produce the wrong solution.", "Contract terms decide who pays; this is not the first step."], concept="Regulatory compliance")

S("B005", "BUSINESS_ENV-T2", "A",
  "A tester finds that the release does not meet mandatory accessibility requirements. The release date is tomorrow. What should the project manager do?",
  ["Release and fix accessibility in a later patch", "Inform the product owner and stakeholders, and do not release until the compliance gap is resolved or formally handled per policy",
   "Ask the tester to mark the issue as minor", "Release only to internal users without telling anyone"],
  "B", "Mandatory requirements are not negotiable trade-offs. Raise the issue transparently and follow policy.",
  ["Knowingly releasing non-compliant software breaches obligations.", None, "Downgrading the issue is unethical.", "Concealment is unethical."],
  tags=("situational",), concept="Compliance in definition of done")

S("B006", "BUSINESS_ENV-T3", "P",
  "A sponsor asks a developer directly to add a new report. The developer tells the project manager. What should the project manager do FIRST?",
  ["Tell the developer to add the report", "Log a change request and evaluate its impact on scope, schedule, cost and risk",
   "Refuse the request", "Ask the change control board to approve it immediately"],
  "B", "In a predictive project, changes are logged and their impact analyzed before the CCB or decision maker decides.",
  ["Implementing before approval bypasses change control.", None, "The request may be valuable.", "The CCB needs an impact analysis first."], concept="Integrated change control")

ORDER("B007", "BUSINESS_ENV-T3", "P", "Arrange the steps of handling a change request in a predictive project.",
      ["Log the change request", "Analyze impact on all constraints", "Submit to the change control board for decision", "Update plans and baselines if approved", "Communicate the decision to stakeholders"],
      "Integrated change control: log → analyze → decide → update → communicate.", concept="Change control")

S("B008", "BUSINESS_ENV-T3", "A", "In an agile project, where should a newly requested feature normally go?",
  ["Into the current sprint immediately", "Into the product backlog for the product owner to prioritize",
   "To the change control board", "Into the risk register"],
  "B", "Agile welcomes change through the product backlog. The product owner orders it by value.",
  ["Changing a sprint mid-way disrupts the sprint goal.", None, "Agile rarely uses a CCB for backlog changes.", "A feature request is not a risk."], tags=(), d=1, concept="Backlog change")

S("B009", "BUSINESS_ENV-T4", "A",
  "In every sprint the team loses two days waiting for database access approvals from another department. What should the scrum master do?",
  ["Ask the team to plan less work", "Escalate the impediment with data on lost time and work with the department to streamline approvals",
   "Tell the team to use production credentials", "Record it in the retrospective and accept it"],
  "B", "Servant leaders remove impediments beyond the team's control, using data to make the case.",
  ["This hides the root cause.", None, "This breaches security policy.", "Accepting a recurring blocker is passive."], concept="Removing impediments")

S("B010", "BUSINESS_ENV-T4", "P", "What is the key difference between an issue and a risk?",
  ["Issues are always larger than risks", "An issue has occurred; a risk is an uncertain future event",
   "Risks are only negative; issues can be positive", "Issues are owned by the sponsor; risks by the PM"],
  "B", "Risks are uncertain and in the future. Issues are current problems that need resolution.",
  ["Size is not the distinction.", None, "Risks can be positive (opportunities).", "Ownership varies."], tags=(), d=1, concept="Issue vs risk")

S("B011", "BUSINESS_ENV-T5", "P",
  "A risk has a 25% probability and a cost impact of 80,000. What is its expected monetary value?",
  ["-20,000", "-60,000", "-80,000", "-25,000"], "A", "EMV = probability × impact = 0.25 × (−80,000) = −20,000.",
  [None, "That is 75% of the impact.", "That is the full impact.", "Not a valid result."], tags=("calculation",), concept="EMV")

CAT("B012", "BUSINESS_ENV-T5", "P", "Classify each risk response as a threat response or an opportunity response.",
    ["Threat response", "Opportunity response"],
    [("Avoid", 0), ("Transfer", 0), ("Mitigate", 0), ("Exploit", 1), ("Share", 1), ("Enhance", 1)],
    "Threats: avoid, transfer, mitigate (and accept, escalate). Opportunities: exploit, share, enhance (and accept, escalate).", concept="Risk responses")

S("B013", "BUSINESS_ENV-T5", "P",
  "The project buys insurance to cover possible equipment damage during shipping. Which risk response is this?",
  ["Avoid", "Transfer", "Mitigate", "Accept"], "B", "Insurance shifts the financial impact to a third party: transfer.",
  ["Avoid removes the threat entirely, e.g. by not shipping.", None, "Mitigate reduces probability or impact, e.g. better packing.", "Accept means no proactive action."], tags=(), d=1, concept="Risk responses")

S("B014", "BUSINESS_ENV-T5", "H",
  "An identified risk occurs, and the planned response is carried out. What should the project manager do NEXT?",
  ["Close the risk register", "Monitor the response's effectiveness and check for secondary or residual risks",
   "Create a new project charter", "Request management reserve"],
  "B", "After implementing a response, monitor its effectiveness and update the registers for residual and secondary risks.",
  ["The register stays active.", None, "Not related.", "Contingency funds the planned response; management reserve is for unknowns."], concept="Risk monitoring")

M("B015", "BUSINESS_ENV-T5", "H", "Which TWO statements about using AI forecasting tools on a project are MOST accurate?",
  ["AI forecasts remove the need for risk management", "AI tools can introduce risks such as biased or inaccurate outputs that need validation",
   "AI-generated estimates should be reviewed by accountable humans before decisions", "AI tools are always compliant with data-protection rules", "AI outputs do not need to be documented"],
  ["B", "C"], "AI can improve forecasting but adds risks (bias, hallucination, data leakage). People stay accountable for decisions.",
  tags=("ai",), concept="AI in project management")

S("B016", "BUSINESS_ENV-T6", "A",
  "A retrospective shows code reviews wait two days on average. What should happen next?",
  ["Record the finding for future projects", "The team agrees a concrete improvement action, tries it in the next sprint and checks the result",
   "The PM mandates that reviews must be done within one hour", "Escalate to management"],
  "B", "Continuous improvement follows PDCA: plan a change, do it, check the effect, act on the result.",
  ["Improvement should apply now, not only later.", None, "Mandates reduce team ownership.", "The team can solve this itself."], concept="Retrospectives / PDCA")

S("B017", "BUSINESS_ENV-T6", "P", "Which Lean concept refers to eliminating activities that add no value for the customer?",
  ["Kaizen", "Waste (muda) reduction", "Gold plating", "Crashing"], "B",
  "Lean focuses on removing waste, such as waiting, handoffs, defects and over-processing, to increase flow.",
  ["Kaizen is the philosophy of continuous small improvement.", None, "Gold plating adds unneeded features.", "Crashing adds resources."], tags=(), d=1, concept="Lean")

S("B018", "BUSINESS_ENV-T7", "H",
  "A new procurement system went live a month ago, but most staff still use the old spreadsheets. What should the project manager do?",
  ["Ask IT to add more features", "Apply change management: identify champions, provide hands-on training, communicate benefits and retire the old spreadsheets",
   "Report that the project is complete", "Escalate the staff to HR"],
  "B", "Low adoption is a people-change problem. Reinforcement, training and champions (as in ADKAR) drive adoption.",
  ["More features don't address adoption.", None, "Benefits are not yet realized.", "Punitive action increases resistance."], concept="ADKAR / adoption")

ORDER("B019", "BUSINESS_ENV-T7", "H", "Arrange the ADKAR change model elements in order.",
      ["Awareness", "Desire", "Knowledge", "Ability", "Reinforcement"],
      "ADKAR: Awareness of the need, Desire to take part, Knowledge of how, Ability to implement, Reinforcement to sustain.", concept="ADKAR")

S("B020", "BUSINESS_ENV-T8", "A",
  "A competitor launches a free product with similar features to the one your team is building. What should the project manager do?",
  ["Continue the plan; the charter is approved", "Facilitate a rapid impact assessment with the product owner and sponsor to revisit priorities and the business case",
   "Cancel the project immediately", "Copy the competitor's features"],
  "B", "External changes can affect the business case. Assess the impact and let the right decision makers adjust direction.",
  ["Ignoring market change risks delivering no value.", None, "Cancellation is not the PM's unilateral decision.", "Copying is not a strategy."], concept="External environment")

MATCH("B021", "BUSINESS_ENV-T8", "P", "Match each external factor to its PESTLE category.",
      [("New import tariff on components", "Political"), ("Rising interest rates", "Economic"), ("Remote-work preferences of staff", "Social"),
       ("New cloud AI service released", "Technological"), ("Carbon-reporting regulation", "Legal / Environmental")],
      expl="PESTLE groups external influences so their impact on the project can be assessed systematically.", concept="PESTLE")

S("B022", "BUSINESS_ENV-T2", "P",
  "The organization requires all projects to report their carbon footprint at phase gates. The vendor cannot provide emissions data. What should the project manager do?",
  ["Skip the requirement for this project", "Treat it as a compliance requirement: log the gap as an issue, work with the vendor on estimation methods, and inform governance",
   "Estimate a number without a method", "Replace the vendor immediately"],
  "B", "Sustainability reporting is an organizational compliance requirement. Manage the gap transparently with a defensible method.",
  ["Requirements cannot be skipped unilaterally.", None, "Unsupported numbers are misleading.", "Replacement is drastic and may not be needed."],
  tags=("sustainability",), d=3, concept="ESG compliance")

S("B023", "BUSINESS_ENV-T1", "A",
  "Portfolio leaders want visibility of several agile teams without adding heavy reporting. What governance approach fits BEST?",
  ["Weekly 20-page status reports from each team", "Lightweight governance using shared roadmaps, portfolio Kanban and regular review events",
   "A phase-gate approval before every sprint", "No governance, because agile teams are self-organizing"],
  "B", "Adaptive governance uses transparency and frequent review events rather than heavy documentation.",
  ["Heavy reporting slows delivery.", None, "Per-sprint gates add bureaucracy.", "Some governance is always needed."], concept="Adaptive governance")

S("B024", "BUSINESS_ENV-T4", "P",
  "A problem keeps recurring even though the team applies the same workaround each time. What should the project manager do?",
  ["Continue applying the workaround", "Perform root cause analysis, such as 5 whys or a fishbone diagram, and address the cause",
   "Add more workaround documentation", "Accept the issue"],
  "B", "Recurring issues call for root cause analysis to prevent recurrence.",
  ["Workarounds treat symptoms.", None, "More documentation still treats symptoms.", "Accepting is passive."], tags=(), concept="Root cause analysis")

# ---------------------------------------------------------------- CASE STUDIES
CASES.append(dict(
    id="CASE-01", title="Clinic appointment platform",
    body=("You lead a 9-person hybrid team building an online appointment platform for a group of 14 health clinics. "
          "The hardware kiosks for clinic lobbies are procured under a fixed-price contract with a predictive schedule. "
          "The patient web and mobile apps are built in two-week sprints. The sponsor is the group's operations director. "
          "Halfway through, a regional health authority publishes new rules on storing patient data. Clinic receptionists, "
          "who will use the system daily, have attended only one of six sprint reviews."),
    exhibits=["Status at week 12: Kiosk contract: 2 of 4 milestones accepted. App: velocity 24, 26, 21, 22. Remaining backlog: 160 points. Budget: BAC 400,000; EV 180,000; AC 210,000; PV 200,000."],
))
S("C101", "BUSINESS_ENV-T2", "H", "Given the new patient-data rules, what should you do FIRST?",
  ["Pause the whole project", "Engage the organization's privacy or compliance lead to assess the impact on both app and kiosk scope",
   "Ask the kiosk vendor to absorb any change", "Add a generic 'compliance' story to the backlog"],
  "B", "Understand the regulatory impact with experts before deciding on backlog items, contract changes or a pause.",
  ["Pausing is premature.", None, "Contract terms decide that later.", "A vague story without analysis won't ensure compliance."], case="CASE-01", d=3)
S("C102", "PROCESS-T6", "P", "Based on the exhibit, what is the cost performance index (CPI), and what does it mean?",
  ["0.86: over budget", "0.90: behind schedule", "1.17: under budget", "0.86: ahead of schedule"],
  "A", "CPI = EV / AC = 180,000 / 210,000 ≈ 0.86. Less than 1 means over budget.",
  [None, "0.90 is SPI (EV/PV), which shows schedule, not cost.", "This inverts the formula.", "CPI is about cost, not schedule."], case="CASE-01", tags=("calculation",))
S("C103", "PEOPLE-T4", "A", "Receptionists rarely attend sprint reviews. What is the BEST way to improve their engagement?",
  ["Report their absence to clinic managers", "Hold short reviews in the clinics at quiet times, or use recorded demos with a quick feedback form",
   "Have the product owner accept stories for them", "Wait until user acceptance testing"],
  "B", "Adapting engagement to the stakeholders' working reality raises participation and feedback quality.",
  ["Escalation without adapting is unlikely to help.", None, "Proxy acceptance risks low adoption.", "Late feedback is expensive."], case="CASE-01")
M("C104", "PROCESS-T5", "P", "The kiosk vendor says the new rules require encrypted storage not in the contract. Which TWO actions are appropriate?",
  ["Follow the contract's change control process to evaluate and agree the change", "Tell the vendor to make the change at no cost because regulation is their problem",
   "Assess the impact of the change on the kiosk milestones and budget", "Switch to a cost-reimbursable contract immediately", "Ignore the kiosks; only the apps store patient data"],
  ["A", "C"], "Contract changes go through the agreed change process with an impact assessment. Unilateral demands or switching contract types are inappropriate.", case="CASE-01")

CASES.append(dict(
    id="CASE-02", title="Warehouse automation rollout",
    body=("Your company is installing automated picking robots in three warehouses over nine months. The project follows a predictive plan with phase gates. "
          "Warehouse staff are anxious about job changes, and the union has asked for a meeting. After installation in the first warehouse, "
          "picking speed improved only 5%, against a business case target of 25%. A supplier delay has used most of the schedule float on the second site."),
    exhibits=["Risk register extract: R7 'Robot supplier delay' – probability 40%, impact 30 days – response: mitigate (secondary supplier pre-qualified)."],
))
S("C201", "BUSINESS_ENV-T7", "H", "Picking speed improved only 5% at the first site. Staff report they still pick some orders manually 'to be safe'. What is the MOST likely focus for improvement?",
  ["Buy faster robots", "Organizational change support: training, reinforcement and involving staff in process redesign", "Cancel the remaining rollouts", "Change the business case target"],
  "B", "Benefits depend on adoption. The symptoms point to people and process change rather than technology.",
  ["The technology may not be the problem.", None, "Premature without root-cause analysis.", "Changing the target hides the problem."], case="CASE-02")
S("C202", "PEOPLE-T4", "P", "The union has requested a meeting. What should you do?",
  ["Decline, because HR handles unions", "Accept, with HR, to listen to concerns and share plans transparently, then update the stakeholder engagement plan",
   "Send a written FAQ instead", "Ask the sponsor to cancel the meeting"],
  "B", "The union is a high-influence stakeholder. Engaging directly and transparently, with HR involved, reduces resistance.",
  ["Avoiding a key stakeholder increases risk.", None, "One-way communication is insufficient here.", "Cancelling damages trust."], case="CASE-02")
S("C203", "BUSINESS_ENV-T5", "P", "The supplier delay risk (R7) has now occurred. What should you do?",
  ["Create a new risk response from scratch", "Implement the planned response (engage the pre-qualified secondary supplier) and update the risk register and issue log",
   "Wait to see whether the supplier recovers", "Use management reserve to pay for overtime"],
  "B", "When an identified risk occurs, carry out its planned response and update the registers. It is now an issue.",
  ["A response already exists.", None, "Waiting wastes the remaining float.", "Overtime is not the planned response, and management reserve is for unknowns."], case="CASE-02")
ORDER("C204", "PROCESS-T10", "P", "The final site is accepted. Order these closing steps.",
      ["Obtain formal acceptance of the final deliverables", "Close the robot supplier contracts", "Transfer support to the operations team", "Finalize lessons learned and archive records", "Release the project team"],
      "Accept → close procurements → transition → lessons and archive → release resources. Some steps may overlap, but this sequence protects the organization.", case="CASE-02")

# ---------------------------------------------------------------- Added after verification review (gap fill:
# thin tasks, agile/hybrid balance, July 2026 themes AI & sustainability)
S("G001", "PEOPLE-T5", "A",
  "At release planning, the product owner and the head of sales disagree on what 'done' means for a reporting feature. What should the project manager do FIRST?",
  ["Use the product owner's definition because they own the backlog", "Facilitate a session to agree explicit acceptance criteria for the feature with both parties",
   "Ask the team to build both versions", "Escalate to the sponsor for a ruling"],
  "B", "Explicit, agreed acceptance criteria align expectations before work starts and prevent rework at the review.",
  ["Ownership of priority does not remove the need to align acceptance criteria with key stakeholders.", None,
   "Building both wastes capacity.", "Escalation is premature before facilitation."], concept="Acceptance criteria")
S("G002", "PEOPLE-T6", "H",
  "A steering committee member keeps asking for detailed weekly reports, while the agile team already publishes a live dashboard. The member says the dashboard 'is hard to read'. What is the BEST response?",
  ["Produce the detailed weekly report as requested", "Meet the member to understand what decisions they need to make and adapt the dashboard or provide a short tailored summary",
   "Tell the member the dashboard is the agile standard", "Remove the member from the distribution list"],
  "B", "Managing expectations starts with understanding the stakeholder's real information needs, then tailoring the format without adding waste.",
  ["This may add effort without meeting the underlying need.", None, "Dismissing the concern damages engagement.", "Excluding a governance stakeholder is inappropriate."], concept="Tailored communication")
S("G003", "PEOPLE-T7", "A",
  "Only one developer understands the payment module, and the team's velocity drops whenever she is away. Which action BEST addresses this?",
  ["Ask her to document the module fully", "Introduce pairing and rotate payment stories across team members",
   "Hire a contractor specialist as a backup", "Add the risk to the register and accept it"],
  "B", "Pairing and story rotation spread tacit knowledge and remove a single point of failure. This is collective code ownership.",
  ["Documentation helps but rarely transfers tacit knowledge.", None, "A contractor creates another silo.", "Acceptance ignores an easy, effective response."], concept="Knowledge sharing")
S("G004", "PROCESS-T9", "A",
  "A release burnup chart shows the completed-work line rising steadily, but the total-scope line is rising just as fast. What does this indicate?",
  ["The team's velocity is too low", "Scope is growing at about the same rate as work is completed, so the release date is at risk",
   "The project is on track", "The chart is incorrectly configured"],
  "B", "A burnup chart shows scope separately. If scope grows as fast as completion, the lines never meet; the product owner must re-plan or reprioritize.",
  ["Velocity looks steady; scope growth is the problem.", None, "Parallel lines mean no convergence.", "This is a normal and useful burnup pattern."], concept="Burnup chart")
S("G005", "BUSINESS_ENV-T6", "H",
  "Retrospective actions are agreed each sprint but rarely implemented. What should the project manager do?",
  ["Stop holding retrospectives", "Limit improvements to one or two actions, add them to the backlog with owners and review them at the next retrospective",
   "Assign all improvement actions to the scrum master", "Report the team to management"],
  "B", "Continuous improvement needs few, visible, owned actions that are checked (PDCA). Putting them in the backlog makes them real work.",
  ["Removing retrospectives removes learning.", None, "Improvement is a whole-team responsibility.", "Punitive action discourages honesty."], concept="Retrospective actions")
S("G006", "BUSINESS_ENV-T8", "H",
  "Midway through a hybrid project, a new trade tariff raises the cost of imported hardware by 20%. What should the project manager do FIRST?",
  ["Absorb the cost using management reserve", "Assess the impact on budget, schedule and business case and inform the sponsor with options",
   "Switch suppliers immediately", "Ask the team to reduce scope to compensate"],
  "B", "External changes are analyzed for impact on the business case before decisions. The sponsor or governance body decides on options.",
  ["Using reserve needs approval and analysis first.", None, "Switching without analysis may add risk.", "Scope changes need stakeholder decisions."], concept="PESTLE / external change")
S("G007", "BUSINESS_ENV-T8", "A",
  "A new AI service appears that could automate a large part of the product the team is building. What is the MOST appropriate action?",
  ["Ignore it until the project ends", "Facilitate a quick spike to assess the service, and review the backlog and business case with the product owner",
   "Cancel the project", "Integrate the service immediately"],
  "B", "Technology shifts are external environment changes. A time-boxed spike gives evidence for the product owner and sponsor to decide.",
  ["Ignoring the change risks building obsolete features.", None, "Cancelling is not the PM's unilateral decision.", "Integrating without assessment adds risk (security, cost, compliance)."],
  tags=("scenario", "ai"), d=3, concept="Spikes, external environment")
S("G008", "PROCESS-T1", "H",
  "Your organization requires all new projects to report expected carbon emissions at the business-case gate. Where should this be addressed FIRST?",
  ["In the closure report", "In planning: add sustainability objectives and metrics to the project management plan and business case",
   "Only if the sponsor asks", "In the lessons-learned register"],
  "B", "Sustainability requirements shape the plan from the start: objectives, metrics, procurement choices and reporting. The July 2026 outline adds sustainability to project scenarios.",
  ["Too late to influence decisions.", None, "It is an organizational requirement.", "Lessons learned don't meet the requirement."],
  tags=("scenario", "sustainability"), concept="Sustainability in planning")
M("G009", "BUSINESS_ENV-T2", "H", "A team wants to use a generative-AI tool to summarize customer interviews. Which TWO actions should come FIRST?",
  ["Check the organization's AI and data-protection policies", "Upload the interviews to test the tool's quality",
   "Confirm customer consent or anonymize data as required", "Let each team member choose their own tool", "Skip review because the summaries are internal"],
  ["A", "C"], "Using AI on personal data is a compliance question first: follow policy and protect personal data (consent, anonymization) before any processing.",
  tags=("ai",), concept="Responsible AI and compliance")
S("G010", "PEOPLE-T3", "A",
  "A team member uses an AI coding assistant and submits code that contains a security flaw. How should the team prevent this in future?",
  ["Ban AI tools", "Add security review and automated scanning of all code, including AI-assisted code, to the definition of done",
   "Make the team member responsible for all security checks", "Rely on the AI tool's own warnings"],
  "B", "Humans remain accountable for AI-assisted output. Building checks into the definition of done applies the control consistently to everyone.",
  ["Bans may be unnecessary and lose productivity.", None, "Quality is a team responsibility.", "Tool warnings are not sufficient assurance."],
  tags=("situational", "ai"), concept="Responsible AI, definition of done")
S("G011", "PROCESS-T3", "H",
  "Benefits analysis shows a delivered feature is rarely used, while users ask for an improvement to another feature. What should the team do?",
  ["Continue enhancing the unused feature as planned", "Reprioritize the backlog toward the requested improvement and consider retiring the unused feature",
   "Wait until the end of the project to decide", "Ask users to use the feature more"],
  "B", "Value-based delivery uses outcome data to change priorities and stops investing in low-value features.",
  ["Planned work that adds no value is waste.", None, "Delaying the decision wastes value.", "The data shows users' needs are elsewhere."], concept="Benefits and outcomes")
CAT("G012", "PROCESS-T1", "H", "For each project element, choose the more suitable approach.",
    ["Predictive", "Adaptive (agile)"],
    [("Building foundations under a fixed building permit", 0), ("A customer mobile app with uncertain feature needs", 1),
     ("Regulatory validation documents with fixed content", 0), ("A marketing website refined through user feedback", 1)],
    "Stable, fixed or regulated work suits predictive planning. Uncertain, feedback-driven work suits adaptive delivery. Combining both in one project is a hybrid approach.",
    concept="Tailoring the approach")
