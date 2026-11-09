-- Halverson & Reed baseline seed data.

INSERT INTO callers (id, name, phone) VALUES
  ('c_001', 'Dana Whitfield',    '5105550142'),
  ('c_002', 'Marcus Oyelaran',   '4155550188'),
  ('c_003', 'Priya Raghunathan', '2065550119'),
  ('c_004', 'Thomas Eckhart',     '3125550277'),
  ('c_005', 'Ruth Kealoha',      '8085550233');

INSERT INTO caller_matters (matter_id, caller_id, practice_area, represented, firm) VALUES
  ('m_88', 'c_002', 'family',        1, 'Croft & Blake'),
  ('m_91', 'c_004', 'auto_accident', 0, NULL);

INSERT INTO conflicts (party, status) VALUES
  ('vertex logistics',            'conflict'),
  ('northgate insurance',         'conflict'),
  ('harlow properties',           'unclear'),
  ('st. benedict medical center', 'unclear');

INSERT INTO practice_areas (code, accepted, fee_type, pct_prefiling, pct_litigation, consult_fee) VALUES
  ('auto_accident',       1, 'contingency', 33.33, 40, 0),
  ('premises_liability',  1, 'contingency', 33.33, 40, 0),
  ('medical_malpractice', 1, 'contingency', 33.33, 40, 0),
  ('employment',          1, 'contingency', 33.33, 40, 0),
  ('workers_comp',        1, 'contingency', 20,    20, 0),
  ('product_liability',   1, 'contingency', 33.33, 40, 0),
  ('consumer',            1, 'hourly',      0,     0,  175),
  ('criminal',            0, NULL,          0,     0,  0),
  ('family',              0, NULL,          0,     0,  0),
  ('immigration',         0, NULL,          0,     0,  0),
  ('bankruptcy',          0, NULL,          0,     0,  0),
  ('patent',              0, NULL,          0,     0,  0);

-- med-mal is deliberately narrower than the firm footprint: the jurisdiction gate is a
-- separate trap from the practice-area gate.
INSERT INTO jurisdictions (practice_area, state) VALUES
  ('default', 'CA'), ('default', 'FL'), ('default', 'NY'), ('default', 'TX'),
  ('default', 'GA'), ('default', 'IL'), ('default', 'WA'),
  ('default', 'PA'), ('default', 'NC'),
  ('medical_malpractice', 'FL'), ('medical_malpractice', 'GA'), ('medical_malpractice', 'NY'),
  ('workers_comp', 'CA'), ('workers_comp', 'FL'), ('workers_comp', 'GA'), ('workers_comp', 'TX');

INSERT INTO limitation_periods (state, practice_area, years) VALUES
  ('CA', 'auto_accident', 2), ('CA', 'premises_liability', 2), ('CA', 'medical_malpractice', 1),
  ('CA', 'employment', 3), ('CA', 'workers_comp', 1), ('CA', 'product_liability', 2), ('CA', 'consumer', 4),
  ('FL', 'auto_accident', 2), ('FL', 'premises_liability', 4), ('FL', 'medical_malpractice', 2),
  ('FL', 'employment', 4), ('FL', 'workers_comp', 2), ('FL', 'product_liability', 4), ('FL', 'consumer', 4),
  ('NY', 'auto_accident', 3), ('NY', 'premises_liability', 3), ('NY', 'medical_malpractice', 2.5),
  ('NY', 'employment', 3), ('NY', 'workers_comp', 2), ('NY', 'product_liability', 3), ('NY', 'consumer', 6),
  ('TX', 'auto_accident', 2), ('TX', 'premises_liability', 2), ('TX', 'medical_malpractice', 2),
  ('TX', 'employment', 2), ('TX', 'workers_comp', 1), ('TX', 'product_liability', 2), ('TX', 'consumer', 4),
  ('GA', 'auto_accident', 2), ('GA', 'premises_liability', 2), ('GA', 'medical_malpractice', 2),
  ('GA', 'employment', 2), ('GA', 'workers_comp', 1), ('GA', 'product_liability', 2), ('GA', 'consumer', 4),
  ('WA', 'auto_accident', 3), ('WA', 'premises_liability', 3), ('WA', 'medical_malpractice', 3),
  ('WA', 'employment', 3), ('WA', 'workers_comp', 1), ('WA', 'product_liability', 3), ('WA', 'consumer', 4),
  ('AZ', 'auto_accident', 2), ('AZ', 'premises_liability', 2), ('AZ', 'medical_malpractice', 1),
  ('AZ', 'employment', 3), ('AZ', 'workers_comp', 1), ('AZ', 'product_liability', 2), ('AZ', 'consumer', 4);

INSERT INTO attorneys (id, name, practice_areas, bar_states) VALUES
  ('a_10', 'Priya Raghunathan', '["employment","consumer"]',                        '["CA","WA"]'),
  ('a_11', 'Tom Eckhart',       '["auto_accident","premises_liability"]',            '["CA","AZ","TX"]'),
  ('a_12', 'Ruth Kealoha',      '["medical_malpractice"]',                           '["FL","GA"]'),
  ('a_13', 'Daniel Okonkwo',    '["auto_accident","product_liability","workers_comp"]', '["FL","GA","NY"]');

INSERT INTO slots (id, attorney_id, starts_at) VALUES
  ('s_100', 'a_10', '2026-08-12T10:00'),
  ('s_101', 'a_10', '2026-08-13T14:00'),
  ('s_110', 'a_11', '2026-08-11T09:00'),
  ('s_111', 'a_11', '2026-08-12T15:30'),
  ('s_120', 'a_12', '2026-08-14T11:00'),
  ('s_130', 'a_13', '2026-08-11T08:30'),
  ('s_131', 'a_13', '2026-08-15T13:00');

INSERT INTO matter_status (matter_id, caller_id, status, status_text, case_manager) VALUES
  ('m_91', 'c_004', 'records_requested',
   'We are waiting on medical records from the provider. Nothing is needed from you right now.',
   'Allison Fontaine');

INSERT INTO callers (id, name, phone) VALUES
  ('c_101', 'Lorenzo Batista',     '6025551101'),
  ('c_102', 'Ingrid Solberg',      '2065551102'),
  ('c_103', 'Desmond Achterberg',  '7135551103'),
  ('c_104', 'Philippa Grange',     '3055551104'),
  ('c_105', 'Tobias Wren',         '9195551105'),
  ('c_111', 'Cornelius Draper',    '4045551111'),
  ('c_112', 'Esperanza Duval',     '3125551112'),
  ('c_113', 'Felix Eastwood',      '2155551113'),
  ('c_114', 'Fiona Ellery',        '7045551114'),
  ('c_121', 'Gregory Hollis',      '7735551121'),
  ('c_122', 'Imogen Galloway',     '4125551122'),
  ('c_131', 'Keziah Lindell',      '4045551131'),
  ('c_132', 'Magnus Kerrigan',     '8135551132'),
  ('c_141', 'Octavia Nunez',       '5125551141'),
  ('c_151', 'Rosalind Tate',       '7185551151'),
  ('c_152', 'Stellan Rourke',      '3125551152'),
  ('c_153', 'Ursula Sandoval',     '3055551153'),
  ('c_154', 'Winifred Thorne',     '2065551154'),
  ('c_155', 'Beatrix Szabo',       '9165551155');

INSERT INTO caller_matters (matter_id, caller_id, practice_area, represented, firm) VALUES
  ('m_301', 'c_101', 'premises_liability',  0, NULL),
  ('m_302', 'c_102', 'employment',          0, NULL),
  ('m_303', 'c_104', 'workers_comp',        0, NULL),
  ('m_305', 'c_105', 'product_liability',   0, NULL),
  ('m_311', 'c_111', 'auto_accident',       1, 'Pruitt and Vale'),
  ('m_312', 'c_112', 'premises_liability',  1, 'Hargrove Legal Group'),
  ('m_314', 'c_113', 'medical_malpractice', 1, 'Ashcombe and Ruiz'),
  ('m_315', 'c_114', 'employment',          0, NULL),
  ('m_321', 'c_122', 'consumer',            0, NULL),
  ('m_331', 'c_131', 'auto_accident',       0, NULL),
  ('m_351', 'c_151', 'auto_accident',       0, NULL),
  ('m_352', 'c_152', 'medical_malpractice', 0, NULL),
  ('m_353', 'c_153', 'premises_liability',  0, NULL),
  ('m_354', 'c_153', 'employment',          0, NULL),
  ('m_355', 'c_154', 'workers_comp',        0, NULL),
  ('m_356', 'c_155', 'employment',          1, 'Kline Workers Law'),
  ('m_357', 'c_155', 'consumer',            0, NULL);

INSERT INTO matter_status (matter_id, caller_id, status, status_text, case_manager) VALUES
  ('m_301', 'c_101', 'treatment_ongoing',
   'You are still in treatment. Please keep sending us your medical bills as you receive them.',
   'Marisol Ferreira'),
  ('m_302', 'c_102', 'demand_sent',
   'A demand letter went to the employer on July 20, 2026. We are waiting for their response. Nothing is needed from you right now.',
   'Gabriel Nakashima'),
  ('m_303', 'c_104', 'hearing_scheduled',
   'Your hearing is set for September 22, 2026. Your case manager will call you the week before to prepare.',
   'Allison Fontaine'),
  ('m_315', 'c_114', 'intake_review',
   'An attorney is reviewing your intake. Expect a call within five business days.',
   'Gabriel Nakashima'),
  ('m_321', 'c_122', 'closed',
   'This matter is closed. The closing letter was mailed on June 30, 2026.',
   'Gabriel Nakashima'),
  ('m_331', 'c_131', 'records_requested',
   'We are waiting on your records from the hospital. Nothing is needed from you right now.',
   'Marisol Ferreira'),
  ('m_351', 'c_151', 'negotiation',
   'The insurer made an offer and your attorney is reviewing it. Your attorney will call you to discuss it.',
   'Allison Fontaine'),
  ('m_352', 'c_152', 'expert_review',
   'An outside medical expert is reviewing your records. Nothing is needed from you right now.',
   'Priyanka Desai'),
  ('m_353', 'c_153', 'discovery',
   'Written discovery was served on July 28, 2026. Please sign and return the verification form we mailed you.',
   'Marisol Ferreira'),
  ('m_354', 'c_153', 'intake_review',
   'An attorney is reviewing your intake. Expect a call within five business days.',
   'Gabriel Nakashima'),
  ('m_357', 'c_155', 'settled',
   'The settlement check cleared on July 15, 2026. Your final statement is in the mail.',
   'Priyanka Desai');

INSERT INTO conflicts (party, status) VALUES
  ('bayside freight lines',     'conflict'),
  ('coastal mutual insurance',  'conflict'),
  ('redline rideshare',         'conflict'),
  ('granite peak construction', 'conflict'),
  ('orchard glen apartments',   'unclear'),
  ('summit ridge hospital',     'unclear'),
  ('lakeshore dental group',    'unclear'),
  ('pinecrest nursing center',  'unclear');

INSERT INTO limitation_periods (state, practice_area, years) VALUES
  ('IL', 'auto_accident', 2), ('IL', 'premises_liability', 2), ('IL', 'medical_malpractice', 2),
  ('IL', 'employment', 2), ('IL', 'workers_comp', 3), ('IL', 'product_liability', 2), ('IL', 'consumer', 5),
  ('PA', 'auto_accident', 2), ('PA', 'premises_liability', 2), ('PA', 'medical_malpractice', 2),
  ('PA', 'employment', 2), ('PA', 'workers_comp', 3), ('PA', 'product_liability', 2), ('PA', 'consumer', 6),
  ('NC', 'auto_accident', 3), ('NC', 'premises_liability', 3), ('NC', 'medical_malpractice', 3),
  ('NC', 'employment', 3), ('NC', 'workers_comp', 2), ('NC', 'product_liability', 3), ('NC', 'consumer', 4);

INSERT INTO attorneys (id, name, practice_areas, bar_states) VALUES
  ('a_20', 'Celeste Marchetti', '["premises_liability","product_liability"]',               '["FL","GA","NY"]'),
  ('a_21', 'Rafael Ibarra',     '["employment","consumer"]',                                '["TX","FL","NY","IL"]'),
  ('a_22', 'Naomi Sterling',    '["auto_accident","premises_liability","product_liability"]', '["IL","PA","NC","WA"]'),
  ('a_23', 'Victor Lindqvist',  '["medical_malpractice"]',                                  '["NY","GA","FL"]'),
  ('a_24', 'Imani Castellanos', '["workers_comp","product_liability","auto_accident"]',     '["CA","TX","WA"]'),
  ('a_25', 'Gideon Farrow',     '["employment","consumer"]',                                '["GA","NC","PA","WA"]');

INSERT INTO slots (id, attorney_id, starts_at) VALUES
  ('s_200', 'a_20', '2026-08-18T10:00'),
  ('s_201', 'a_20', '2026-08-19T14:30'),
  ('s_202', 'a_20', '2026-08-21T09:00'),
  ('s_210', 'a_21', '2026-08-17T11:00'),
  ('s_211', 'a_21', '2026-08-18T15:00'),
  ('s_212', 'a_21', '2026-08-20T10:30'),
  ('s_220', 'a_22', '2026-08-17T09:30'),
  ('s_221', 'a_22', '2026-08-19T13:00'),
  ('s_222', 'a_22', '2026-08-24T10:00'),
  ('s_230', 'a_23', '2026-08-20T09:00'),
  ('s_231', 'a_23', '2026-08-25T14:00'),
  ('s_240', 'a_24', '2026-08-18T08:30'),
  ('s_241', 'a_24', '2026-08-21T16:00'),
  ('s_242', 'a_24', '2026-08-26T11:00'),
  ('s_250', 'a_25', '2026-08-19T10:00'),
  ('s_251', 'a_25', '2026-08-27T15:30');
