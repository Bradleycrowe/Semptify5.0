// ==========================================
// LEGAL VOCABULARY DATABASE & PANEL
// Shared across all Semptify document pages
// ==========================================

const legalVocabulary = [
    // PLEADINGS
    { word: "Complaint", cat: "pleadings", def: "The initial document filed by the plaintiff that starts a lawsuit, stating the claims against the defendant.", example: "The Complaint filed against me contains factual errors that I will address in my Answer." },
    { word: "Answer", cat: "pleadings", def: "The defendant's formal written response to the complaint, admitting or denying each allegation.", example: "I hereby submit my Answer to the Complaint, denying the allegations in paragraphs 3 through 7." },
    { word: "Counterclaim", cat: "pleadings", def: "A claim made by a defendant against the plaintiff in the same lawsuit.", example: "In addition to my Answer, I am filing a Counterclaim for the Plaintiff's failure to maintain habitable conditions." },
    { word: "Affirmative Defense", cat: "pleadings", def: "A defense that introduces new facts to defeat the plaintiff's claim, even if the plaintiff's allegations are true.", example: "I assert the affirmative defense of retaliatory eviction under state law." },
    { word: "Summons", cat: "pleadings", def: "An official court document notifying a defendant that a lawsuit has been filed and requiring a response.", example: "I received the Summons on [date] and am responding within the required timeframe." },
    { word: "Petition", cat: "pleadings", def: "A formal written request to the court asking for a specific action or order.", example: "I respectfully submit this Petition requesting the court to..." },
    { word: "Cross-Complaint", cat: "pleadings", def: "A complaint filed by the defendant against another party, including the plaintiff or a third party.", example: "I file this Cross-Complaint against the property management company for negligence." },
    { word: "Demurrer", cat: "pleadings", def: "A formal objection claiming the complaint fails to state a valid legal claim even if all facts are true.", example: "I demur to the Complaint on grounds that it fails to state facts sufficient to constitute a cause of action." },
    
    // MOTIONS
    { word: "Motion", cat: "motions", def: "A formal request asking the court to make a specific ruling or order.", example: "I file this Motion requesting the Court to dismiss the case for lack of proper notice." },
    { word: "Motion to Dismiss", cat: "motions", def: "A request asking the court to throw out a case for legal deficiencies.", example: "Defendant respectfully moves to dismiss this action based on Plaintiff's failure to provide proper notice as required by law." },
    { word: "Motion for Continuance", cat: "motions", def: "A request to postpone a court date or deadline.", example: "I request a continuance to allow adequate time to gather evidence and prepare my defense." },
    { word: "Motion to Compel", cat: "motions", def: "A request asking the court to order the other party to take a required action, usually related to discovery.", example: "I file this Motion to Compel the landlord to produce maintenance records." },
    { word: "Motion for Summary Judgment", cat: "motions", def: "A request for the court to rule in your favor without a trial because there are no disputed facts.", example: "The undisputed facts establish that Plaintiff failed to provide required notice, warranting summary judgment." },
    { word: "Motion to Stay", cat: "motions", def: "A request to temporarily halt proceedings or enforcement of a judgment.", example: "I request a stay of execution pending the outcome of my appeal." },
    { word: "Motion in Limine", cat: "motions", def: "A pretrial motion asking the court to exclude certain evidence from trial.", example: "I move in limine to exclude any reference to matters outside the scope of this eviction." },
    { word: "Motion to Quash", cat: "motions", def: "A request to invalidate a legal document or proceeding, often used for defective service.", example: "I move to quash service of the summons as it was not properly served according to law." },
    { word: "Motion for Reconsideration", cat: "motions", def: "A request asking the court to review and change a previous ruling.", example: "I move for reconsideration of the Court's order based on newly discovered evidence." },
    { word: "Motion to Set Aside", cat: "motions", def: "A request to vacate or cancel a previous judgment or order.", example: "I move to set aside the default judgment due to excusable neglect." },
    { word: "Motion for Protective Order", cat: "motions", def: "A request for the court to protect a party from harassment, abuse, or improper discovery.", example: "I seek a protective order limiting the scope of defendant's discovery requests." },
    
    // EVIDENCE
    { word: "Exhibit", cat: "evidence", def: "A document or object presented as evidence in court.", example: "Attached hereto as Exhibit A is a photograph documenting the mold conditions." },
    { word: "Affidavit", cat: "evidence", def: "A written statement of facts made under oath.", example: "I submit this Affidavit attesting to the facts described herein under penalty of perjury." },
    { word: "Declaration", cat: "evidence", def: "A written statement of facts, similar to an affidavit but typically not notarized.", example: "I declare under penalty of perjury that the foregoing is true and correct." },
    { word: "Testimony", cat: "evidence", def: "Statements made by witnesses under oath.", example: "My testimony will demonstrate that the landlord was notified of these issues on multiple occasions." },
    { word: "Hearsay", cat: "evidence", def: "An out-of-court statement offered to prove the truth of the matter asserted, generally inadmissible.", example: "I object to this statement as hearsay not falling within any recognized exception." },
    { word: "Burden of Proof", cat: "evidence", def: "The obligation to prove allegations; in civil cases, usually 'preponderance of the evidence.'", example: "The Plaintiff bears the burden of proof to establish that rent was not paid." },
    { word: "Prima Facie", cat: "evidence", def: "Evidence sufficient to establish a fact unless rebutted.", example: "These photographs establish a prima facie case of habitability violations." },
    { word: "Discovery", cat: "evidence", def: "The pretrial process of exchanging relevant information between parties.", example: "Through discovery, I request all maintenance records for the property." },
    { word: "Subpoena", cat: "evidence", def: "A court order requiring a person to appear in court or produce documents.", example: "I have issued a subpoena for the property manager's maintenance logs." },
    { word: "Deposition", cat: "evidence", def: "Sworn testimony taken outside of court, typically recorded by a court reporter.", example: "During the deposition, the landlord admitted to knowing about the mold." },
    { word: "Interrogatories", cat: "evidence", def: "Written questions sent to the opposing party that must be answered under oath.", example: "Please respond to the following interrogatories within 30 days." },
    { word: "Request for Production", cat: "evidence", def: "A formal request for the other party to provide specific documents or evidence.", example: "I request production of all communications regarding the property's condition." },
    { word: "Admissible", cat: "evidence", def: "Evidence that meets legal standards and can be considered by the court.", example: "These photographs are admissible as they are properly authenticated and relevant." },
    
    // PARTIES
    { word: "Plaintiff", cat: "parties", def: "The party who initiates a lawsuit.", example: "The Plaintiff (landlord) has failed to prove their case." },
    { word: "Defendant", cat: "parties", def: "The party being sued or accused in a lawsuit.", example: "As the Defendant, I deny the allegations set forth in the Complaint." },
    { word: "Petitioner", cat: "parties", def: "The party who files a petition with the court.", example: "Petitioner respectfully requests the Court grant the following relief." },
    { word: "Respondent", cat: "parties", def: "The party who responds to a petition.", example: "Respondent opposes the motion for the following reasons." },
    { word: "Pro Se", cat: "parties", def: "Representing oneself in court without an attorney.", example: "I am appearing pro se in this matter and request the Court's consideration." },
    { word: "Counsel", cat: "parties", def: "An attorney or legal representative.", example: "I have not yet retained counsel but intend to seek legal assistance." },
    { word: "Third Party", cat: "parties", def: "A person or entity involved in a matter but not one of the original parties.", example: "The third-party property manager is also liable for these conditions." },
    { word: "Intervenor", cat: "parties", def: "A party who petitions to join an existing lawsuit.", example: "The tenant association moves to intervene in this action." },
    { word: "Amicus Curiae", cat: "parties", def: "A 'friend of the court' who offers information or expertise on a case.", example: "The housing advocacy group filed an amicus brief supporting tenant rights." },
    
    // PROCEDURES
    { word: "Jurisdiction", cat: "procedures", def: "The court's authority to hear and decide a case.", example: "This Court has jurisdiction over this matter pursuant to state housing law." },
    { word: "Venue", cat: "procedures", def: "The proper geographic location for a case to be heard.", example: "Venue is proper in this county as it is where the rental property is located." },
    { word: "Service of Process", cat: "procedures", def: "The formal delivery of legal documents to a party.", example: "I was not properly served as required by law, as the notice was left at an incorrect address." },
    { word: "Due Process", cat: "procedures", def: "The constitutional right to fair legal proceedings.", example: "My due process rights were violated when I was not given adequate notice." },
    { word: "Stipulation", cat: "procedures", def: "An agreement between parties on certain facts or procedures.", example: "The parties stipulate to the following facts." },
    { word: "Continuance", cat: "procedures", def: "A postponement of a court proceeding to a later date.", example: "I request a continuance to obtain legal representation." },
    { word: "Default Judgment", cat: "procedures", def: "A judgment entered against a party who fails to respond or appear.", example: "I request the Court set aside the default judgment as I did not receive proper notice." },
    { word: "Appeal", cat: "procedures", def: "A request to a higher court to review a lower court's decision.", example: "I intend to appeal this decision on the grounds of legal error." },
    { word: "Stay of Execution", cat: "procedures", def: "A court order temporarily preventing enforcement of a judgment.", example: "I request a stay of execution of the eviction order pending my appeal." },
    { word: "Hearing", cat: "procedures", def: "A proceeding before a judge where parties present arguments or evidence.", example: "I request a hearing on this motion at the Court's earliest convenience." },
    { word: "Trial", cat: "procedures", def: "A formal examination of evidence and determination of legal claims.", example: "I am prepared to present evidence at trial supporting my defense." },
    { word: "Judgment", cat: "procedures", def: "The court's final decision in a case.", example: "I request judgment in my favor based on the evidence presented." },
    { word: "Order", cat: "procedures", def: "A written directive from the court requiring specific action.", example: "I respectfully request the Court issue an order compelling production of documents." },
    { word: "Filing", cat: "procedures", def: "The act of submitting documents to the court for official record.", example: "I am filing this response within the time allowed by law." },
    { word: "Statute of Limitations", cat: "procedures", def: "The deadline by which a lawsuit must be filed.", example: "This claim is barred by the statute of limitations." },
    
    // HOUSING-SPECIFIC
    { word: "Unlawful Detainer", cat: "housing", def: "The legal action to evict a tenant; the formal name for an eviction lawsuit.", example: "The Unlawful Detainer action filed against me lacks merit for the following reasons." },
    { word: "Writ of Possession", cat: "housing", def: "A court order authorizing the sheriff to remove a tenant from the property.", example: "I request the Court not issue a Writ of Possession until I have exhausted my appeals." },
    { word: "Notice to Quit", cat: "housing", def: "A notice informing a tenant they must leave the property.", example: "The Notice to Quit was defective because it did not comply with the required timeframe." },
    { word: "Habitability", cat: "housing", def: "The legal requirement that rental property be fit for human habitation.", example: "The landlord breached the implied warranty of habitability by failing to address mold and pest issues." },
    { word: "Rent Withholding", cat: "housing", def: "A tenant's legal right to withhold rent due to uninhabitable conditions.", example: "I exercised my right to rent withholding after the landlord failed to make necessary repairs." },
    { word: "Retaliatory Eviction", cat: "housing", def: "An illegal eviction in response to a tenant exercising their legal rights.", example: "This eviction is retaliatory, filed within 90 days of my complaint to the housing authority." },
    { word: "Security Deposit", cat: "housing", def: "Money held by the landlord as protection against damage or unpaid rent.", example: "The landlord has failed to return my security deposit as required by law." },
    { word: "Lease Violation", cat: "housing", def: "A breach of the terms of the rental agreement.", example: "I deny the alleged lease violation and provide evidence to the contrary." },
    { word: "Constructive Eviction", cat: "housing", def: "When conditions make the property uninhabitable, forcing the tenant to leave.", example: "The landlord's failure to provide heat constituted constructive eviction." },
    { word: "Quiet Enjoyment", cat: "housing", def: "A tenant's right to use and enjoy the property without interference.", example: "The landlord's repeated unannounced entries violated my right to quiet enjoyment." },
    { word: "Cure or Quit", cat: "housing", def: "A notice giving a tenant time to fix a lease violation or leave.", example: "I cured the violation within the timeframe specified in the Cure or Quit notice." },
    { word: "Just Cause", cat: "housing", def: "A legally valid reason for eviction required in some jurisdictions.", example: "The landlord has not established just cause for this eviction as required by local ordinance." },
    { word: "Rent Control", cat: "housing", def: "Laws limiting how much landlords can increase rent.", example: "This rent increase violates the local rent control ordinance." },
    { word: "Fair Housing", cat: "housing", def: "Laws prohibiting housing discrimination based on protected characteristics.", example: "The landlord's actions constitute a violation of the Fair Housing Act." },
    { word: "Landlord Retaliation", cat: "housing", def: "Illegal actions by landlord in response to tenant exercising rights.", example: "The timing of this eviction suggests landlord retaliation for reporting code violations." },
    { word: "Implied Warranty", cat: "housing", def: "Legal guarantees that exist even if not written in the lease.", example: "The implied warranty of habitability requires the landlord to maintain the premises." },
    { word: "Holdover Tenant", cat: "housing", def: "A tenant who remains after the lease expires without landlord permission.", example: "I am not a holdover tenant as my lease automatically renewed month-to-month." },
    { word: "Abandonment", cat: "housing", def: "When a tenant leaves the property without notice before the lease ends.", example: "I did not abandon the premises; I was constructively evicted by uninhabitable conditions." },
    
    // LEGAL PHRASES
    { word: "Pursuant to", cat: "phrases", def: "In accordance with; following the requirements of.", example: "Pursuant to Minnesota Statute § 504B.321, proper notice was not provided." },
    { word: "Hereby", cat: "phrases", def: "By means of this document or statement.", example: "I hereby deny all allegations in the Complaint." },
    { word: "Wherefore", cat: "phrases", def: "For which reason; therefore (used before stating relief requested).", example: "Wherefore, Defendant requests that this Court dismiss the action with prejudice." },
    { word: "Herein", cat: "phrases", def: "In this document.", example: "The facts set forth herein demonstrate the landlord's negligence." },
    { word: "Aforementioned", cat: "phrases", def: "Previously mentioned in this document.", example: "The aforementioned violations constitute grounds for my defense." },
    { word: "Without Prejudice", cat: "phrases", def: "Without affecting any existing legal rights or future claims.", example: "This dismissal should be without prejudice to allow refiling if needed." },
    { word: "With Prejudice", cat: "phrases", def: "Final dismissal that bars refiling of the same claim.", example: "I request dismissal with prejudice due to Plaintiff's repeated violations." },
    { word: "Inter Alia", cat: "phrases", def: "Among other things.", example: "The landlord's violations include, inter alia, failure to maintain heating systems." },
    { word: "Bona Fide", cat: "phrases", def: "In good faith; genuine.", example: "This is a bona fide dispute regarding the condition of the premises." },
    { word: "Res Judicata", cat: "phrases", def: "A matter already decided that cannot be relitigated.", example: "This issue was resolved in the prior proceeding and is barred by res judicata." },
    { word: "Pro Bono", cat: "phrases", def: "Legal services provided free of charge.", example: "I am seeking pro bono legal assistance due to financial hardship." },
    { word: "Sua Sponte", cat: "phrases", def: "On the court's own motion, without a request from either party.", example: "The Court may sua sponte dismiss cases that lack merit." },
    { word: "Nunc Pro Tunc", cat: "phrases", def: "Retroactive legal action, as if done at an earlier time.", example: "I request the order be entered nunc pro tunc to the original filing date." }
];

// ==========================================
// PANEL INJECTION & FUNCTIONALITY
// ==========================================

class LegalVocabPanel {
    constructor() {
        this.currentCategory = 'all';
        this.usedTerms = new Set();
        this.targetTextarea = null;
    }

    init(targetTextareaId = null) {
        this.injectStyles();
        this.injectHTML();
        this.renderVocab(legalVocabulary);
        this.targetTextarea = targetTextareaId ? document.getElementById(targetTextareaId) : null;
        
        // Auto-detect textarea if not specified
        if (!this.targetTextarea) {
            this.targetTextarea = document.querySelector('textarea');
        }
    }

    injectStyles() {
        if (document.getElementById('vocab-panel-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'vocab-panel-styles';
        styles.textContent = `
            /* Legal Vocabulary Panel */
            .vocab-toggle {
                position: fixed;
                right: 0;
                top: 50%;
                transform: translateY(-50%);
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                color: white;
                border: none;
                padding: 1rem 0.5rem;
                border-radius: 8px 0 0 8px;
                cursor: pointer;
                writing-mode: vertical-rl;
                text-orientation: mixed;
                font-weight: 600;
                font-size: 0.85rem;
                z-index: 1000;
                transition: all 0.3s;
                box-shadow: -2px 0 10px rgba(0,0,0,0.2);
            }

            .vocab-toggle:hover {
                padding-right: 0.75rem;
                box-shadow: -4px 0 20px rgba(99, 102, 241, 0.4);
            }

            .vocab-panel {
                position: fixed;
                right: -420px;
                top: 0;
                width: 420px;
                height: 100vh;
                background: #1e293b;
                border-left: 1px solid rgba(255,255,255,0.1);
                z-index: 1001;
                transition: right 0.3s ease;
                display: flex;
                flex-direction: column;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }

            .vocab-panel.open {
                right: 0;
            }

            .vocab-header {
                padding: 1rem 1.5rem;
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .vocab-header h3 {
                margin: 0;
                font-size: 1.1rem;
                color: white;
            }

            .vocab-close {
                background: none;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
                opacity: 0.8;
                line-height: 1;
            }

            .vocab-close:hover { opacity: 1; }

            .vocab-search {
                padding: 1rem;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .vocab-search input {
                width: 100%;
                padding: 0.75rem 1rem;
                background: #0f172a;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: #f8fafc;
                font-size: 0.9rem;
            }

            .vocab-search input::placeholder { color: #64748b; }

            .vocab-search input:focus {
                outline: none;
                border-color: #6366f1;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
            }

            .vocab-categories {
                display: flex;
                flex-wrap: wrap;
                gap: 0.4rem;
                padding: 0.75rem 1rem;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .vocab-cat {
                padding: 0.35rem 0.7rem;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 20px;
                font-size: 0.75rem;
                cursor: pointer;
                transition: all 0.2s;
                color: #94a3b8;
            }

            .vocab-cat:hover, .vocab-cat.active {
                background: #6366f1;
                border-color: #6366f1;
                color: white;
            }

            .vocab-content {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
            }

            .vocab-term {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 0.875rem 1rem;
                margin-bottom: 0.75rem;
                cursor: pointer;
                transition: all 0.2s;
            }

            .vocab-term:hover {
                border-color: #6366f1;
                transform: translateX(-4px);
                background: rgba(99, 102, 241, 0.1);
            }

            .vocab-term .word {
                font-weight: 600;
                color: #818cf8;
                margin-bottom: 0.35rem;
                font-size: 0.95rem;
            }

            .vocab-term .def {
                font-size: 0.82rem;
                color: #94a3b8;
                margin-bottom: 0.5rem;
                line-height: 1.5;
            }

            .vocab-term .example {
                font-size: 0.78rem;
                font-style: italic;
                color: #64748b;
                background: rgba(99, 102, 241, 0.1);
                padding: 0.5rem 0.75rem;
                border-radius: 6px;
                border-left: 3px solid #6366f1;
                line-height: 1.4;
            }

            .vocab-term .insert-hint {
                font-size: 0.7rem;
                color: #22c55e;
                margin-top: 0.5rem;
                opacity: 0;
                transition: opacity 0.2s;
            }

            .vocab-term:hover .insert-hint {
                opacity: 1;
            }

            .vocab-footer {
                padding: 0.875rem 1rem;
                border-top: 1px solid rgba(255,255,255,0.1);
                background: rgba(0,0,0,0.2);
                font-size: 0.78rem;
                color: #64748b;
                text-align: center;
            }

            .vocab-footer i { margin-right: 0.5rem; }

            /* Toast notification */
            .vocab-toast {
                position: fixed;
                bottom: 2rem;
                left: 50%;
                transform: translateX(-50%) translateY(100px);
                background: linear-gradient(135deg, #22c55e, #16a34a);
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 500;
                z-index: 2000;
                transition: transform 0.3s ease;
                box-shadow: 0 4px 20px rgba(34, 197, 94, 0.3);
            }

            .vocab-toast.show {
                transform: translateX(-50%) translateY(0);
            }

            /* Term counter badge */
            .vocab-count {
                background: rgba(0,0,0,0.2);
                padding: 0.2rem 0.5rem;
                border-radius: 10px;
                font-size: 0.7rem;
                margin-left: 0.5rem;
            }

            @media (max-width: 768px) {
                .vocab-panel {
                    width: 100%;
                    right: -100%;
                }
                .vocab-toggle {
                    padding: 0.75rem 0.4rem;
                    font-size: 0.75rem;
                }
            }
        `;
        document.head.appendChild(styles);
    }

    injectHTML() {
        if (document.getElementById('vocabPanel')) return;

        const html = `
            <!-- Legal Vocabulary Toggle -->
            <button class="vocab-toggle" onclick="vocabPanel.toggle()">
                📚 Legal Terms
            </button>

            <!-- Legal Vocabulary Panel -->
            <div class="vocab-panel" id="vocabPanel">
                <div class="vocab-header">
                    <h3>⚖️ Courtroom Vocabulary</h3>
                    <button class="vocab-close" onclick="vocabPanel.toggle()">&times;</button>
                </div>
                <div class="vocab-search">
                    <input type="text" id="vocabSearch" placeholder="Search legal terms..." oninput="vocabPanel.filter()">
                </div>
                <div class="vocab-categories" id="vocabCategories">
                    <span class="vocab-cat active" data-cat="all" onclick="vocabPanel.filterCategory('all')">All <span class="vocab-count">${legalVocabulary.length}</span></span>
                    <span class="vocab-cat" data-cat="pleadings" onclick="vocabPanel.filterCategory('pleadings')">Pleadings</span>
                    <span class="vocab-cat" data-cat="motions" onclick="vocabPanel.filterCategory('motions')">Motions</span>
                    <span class="vocab-cat" data-cat="evidence" onclick="vocabPanel.filterCategory('evidence')">Evidence</span>
                    <span class="vocab-cat" data-cat="parties" onclick="vocabPanel.filterCategory('parties')">Parties</span>
                    <span class="vocab-cat" data-cat="procedures" onclick="vocabPanel.filterCategory('procedures')">Procedures</span>
                    <span class="vocab-cat" data-cat="housing" onclick="vocabPanel.filterCategory('housing')">Housing</span>
                    <span class="vocab-cat" data-cat="phrases" onclick="vocabPanel.filterCategory('phrases')">Phrases</span>
                </div>
                <div class="vocab-content" id="vocabContent"></div>
                <div class="vocab-footer">
                    💡 Click any term to insert • Hover for usage example
                </div>
            </div>

            <!-- Toast notification -->
            <div class="vocab-toast" id="vocabToast">Term inserted!</div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', html);
    }

    toggle() {
        document.getElementById('vocabPanel').classList.toggle('open');
    }

    renderVocab(terms) {
        const container = document.getElementById('vocabContent');
        if (!container) return;
        
        container.innerHTML = terms.map(term => `
            <div class="vocab-term" onclick="vocabPanel.insert('${term.word.replace(/'/g, "\\'")}')">
                <div class="word">${term.word}</div>
                <div class="def">${term.def}</div>
                <div class="example">"${term.example}"</div>
                <div class="insert-hint">✓ Click to insert into your document</div>
            </div>
        `).join('');
    }

    filterCategory(cat) {
        this.currentCategory = cat;
        document.querySelectorAll('.vocab-cat').forEach(c => c.classList.remove('active'));
        document.querySelector(`.vocab-cat[data-cat="${cat}"]`)?.classList.add('active');
        
        const filtered = cat === 'all' 
            ? legalVocabulary 
            : legalVocabulary.filter(t => t.cat === cat);
        
        this.renderVocab(filtered);
    }

    filter() {
        const query = document.getElementById('vocabSearch')?.value.toLowerCase() || '';
        let filtered = legalVocabulary;
        
        if (this.currentCategory !== 'all') {
            filtered = filtered.filter(t => t.cat === this.currentCategory);
        }
        
        if (query) {
            filtered = filtered.filter(t => 
                t.word.toLowerCase().includes(query) || 
                t.def.toLowerCase().includes(query) ||
                t.example.toLowerCase().includes(query)
            );
        }
        
        this.renderVocab(filtered);
    }

    insert(term) {
        // Try to find any active textarea or contenteditable
        let target = this.targetTextarea;
        
        if (!target) {
            target = document.querySelector('textarea:focus') || 
                     document.querySelector('[contenteditable="true"]:focus') ||
                     document.querySelector('textarea') ||
                     document.querySelector('[contenteditable="true"]');
        }
        
        if (target) {
            if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') {
                const start = target.selectionStart || 0;
                const end = target.selectionEnd || 0;
                const text = target.value;
                target.value = text.substring(0, start) + term + text.substring(end);
                target.selectionStart = target.selectionEnd = start + term.length;
                target.focus();
            } else if (target.contentEditable === 'true') {
                // For contenteditable elements
                document.execCommand('insertText', false, term);
            }
            this.showToast(`"${term}" inserted!`);
        } else {
            // Copy to clipboard as fallback
            navigator.clipboard.writeText(term).then(() => {
                this.showToast(`"${term}" copied to clipboard!`);
            });
        }
        
        this.usedTerms.add(term);
    }

    showToast(message) {
        const toast = document.getElementById('vocabToast');
        if (toast) {
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }
    }
}

// Global instance
const vocabPanel = new LegalVocabPanel();

// Auto-init when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => vocabPanel.init());
} else {
    vocabPanel.init();
}
