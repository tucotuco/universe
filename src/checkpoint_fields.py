"""5D2A fixed field vocabulary, reviewed against native constructors/writers.

Not runtime-discovered. Optional lifecycle fields remain optional. This table
rejects extensions; it does NOT by itself prove field semantics or closure.
Dataclass fields are required. Core mutable required fields are checked by
native preflight and the explicit adapters. Unknown types remain unsupported.
"""
FIELD_ADAPTERS = {
    'abilities.Abilities': {
        "allowed": 'abilities'.split(),
        "required": 'abilities'.split(),
    },
    'action.Action': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle actor_id canceled_at cancellation_reason end_time event_type id instrument_id location name parent_event_id resolution start_position start_time strategy target_id threat_at_schedule type universe'.split(),
        "required": 'actor_id end_time event_type instrument_id location name parent_event_id resolution start_time strategy target_id type universe'.split(),
    },
    'action_choice.ChoiceBook': {
        "allowed": '_choices _closed_drafts _counter _drafts _registered _reservations _states _tokens encounter lock revision'.split(),
        "required": '_choices _closed_drafts _counter _drafts _registered _reservations _states _tokens encounter lock'.split(),
    },
    'action_choice.ChoiceMember': {
        "allowed": 'action key target_action_key'.split(),
        "required": 'action key target_action_key'.split(),
    },
    'action_choice.ChoiceView': {
        "allowed": 'action_ids first_start id state version'.split(),
        "required": 'action_ids first_start id state version'.split(),
    },
    'action_choice.Reservation': {
        "allowed": 'action_id boundary choice_id object_id start'.split(),
        "required": 'action_id boundary choice_id object_id start'.split(),
    },
    'action_choice._Accepted': {
        "allowed": 'members origin prepared signatures view'.split(),
        "required": 'members origin prepared signatures view'.split(),
    },
    'action_evaluation.ActionProposal': {
        "allowed": 'action_id actor_id defenses effects metadata outcome target_ids'.split(),
        "required": 'action_id actor_id defenses effects metadata outcome target_ids'.split(),
    },
    'action_evaluation.ActionView': {
        "allowed": 'actor_id boundary data family id instrument_id lifecycle nominal_end order priority start target_id'.split(),
        "required": 'actor_id boundary data family id instrument_id lifecycle nominal_end order priority start target_id'.split(),
    },
    'action_evaluation.AwarenessEffect': {
        "allowed": 'basis distance max_distance observed_id source_action_id target_id'.split(),
        "required": 'basis distance max_distance observed_id source_action_id target_id'.split(),
    },
    'action_evaluation.DamageEffect': {
        "allowed": 'amount component source_action_id target_id'.split(),
        "required": 'amount component source_action_id target_id'.split(),
    },
    'action_evaluation.DefenseEffect': {
        "allowed": 'eligible kind source_action_id strike_id success'.split(),
        "required": 'eligible kind source_action_id strike_id success'.split(),
    },
    'action_evaluation.EffectIdentity': {
        "allowed": 'boundary channel encounter_id slot source_action_id'.split(),
        "required": 'boundary channel encounter_id slot source_action_id'.split(),
    },
    'action_evaluation.FatalEffect': {
        "allowed": 'source_action_id target_id'.split(),
        "required": 'source_action_id target_id'.split(),
    },
    'action_evaluation.IdentifiedEffect': {
        "allowed": 'effect identity'.split(),
        "required": 'effect identity'.split(),
    },
    'action_evaluation.PracticeEffect': {
        "allowed": 'experience skill source_action_id target_id'.split(),
        "required": 'experience skill source_action_id target_id'.split(),
    },
    'action_evaluation.ProtectionEffect': {
        "allowed": 'incoming intercepted layer passed source_action_id target_id'.split(),
        "required": 'incoming intercepted layer passed source_action_id target_id'.split(),
    },
    'action_settlement.TargetCandidate': {
        "allowed": 'actual_damage aware_of category fatal_effect_ids incoming observer_state outgoing_effect_ids practice_state projected_hp starting_hp target_id'.split(),
        "required": 'actual_damage aware_of category fatal_effect_ids incoming observer_state outgoing_effect_ids practice_state projected_hp starting_hp target_id'.split(),
    },
    'actiondictionary.ActionDefinition': {
        "allowed": 'is_melee name required_skill target_type'.split(),
        "required": 'is_melee name required_skill target_type'.split(),
    },
    'actiondictionary.ActionDictionary': {
        "allowed": 'actions'.split(),
        "required": 'actions'.split(),
    },
    'activities.RunAction': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle actor_id canceled_at cancellation_reason displacement end_time event_type id instrument_id location minimum_distance name parent_event_id practice_experience resolution start_position start_time strategy target_id type universe'.split(),
        "required": 'actor_id displacement end_time event_type instrument_id location minimum_distance name parent_event_id practice_experience resolution start_position start_time strategy target_id type universe'.split(),
    },
    'activities.SpotAction': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle _encounter actor_id canceled_at cancellation_reason declared_roll end_time event_type group_fully_visible id instrument_id ledger location name parent_event_id path_status resolution roll spotting_conditions start_position start_time strategy target_id threat_at_schedule type universe'.split(),
        "required": '_encounter actor_id declared_roll end_time event_type group_fully_visible instrument_id ledger location name parent_event_id path_status resolution roll spotting_conditions start_time strategy target_id type universe'.split(),
    },
    'armor.ArmorDefinition': {
        "allowed": 'armor_check_penalty cost defenses dexterity_check_penalty discovery_dc hardness height hit_points is_magical length obj_type tags weapon_categories weight width'.split(),
        "required": 'armor_check_penalty cost defenses dexterity_check_penalty discovery_dc hardness height hit_points is_magical length obj_type tags weapon_categories weight width'.split(),
    },
    'armor.ArmorDictionary': {
        "allowed": 'object_categories objects'.split(),
        "required": 'object_categories objects'.split(),
    },
    'armor.ArmorInstance': {
        "allowed": '_atomic_target_history current front_facing geometry id name original parent_container_id spatial_state top_facing type visual_occlusion'.split(),
        "required": 'current front_facing geometry name original parent_container_id spatial_state top_facing type visual_occlusion'.split(),
    },
    'atomic_publication.ObjectiveCommitProvenance': {
        "allowed": 'boundary consumers encounter_id key origins requesters revision'.split(),
        "required": 'boundary consumers encounter_id key origins requesters revision'.split(),
    },
    'atomic_publication.PublishedInterval': {
        "allowed": 'action_ids boundary committed effect_ids encounter_id inspection notification_intents rng_state'.split(),
        "required": 'action_ids boundary committed effect_ids encounter_id inspection notification_intents rng_state'.split(),
    },
    'atomic_publication.TargetIntervalRecord': {
        "allowed": 'boundary encounter_id state'.split(),
        "required": 'boundary encounter_id state'.split(),
    },
    'being.BeingDefinition': {
        "allowed": 'abilities actions alignment armor_class armor_id body_parts challenge_rating cost discovery_dc experience hardness height hit_dice hit_points immunities is_magical languages length max_speed obj_type physiology_id psionics race reactions resistances senses skills spells states tags traits vulnerabilities weapon_categories weight width'.split(),
        "required": 'abilities actions alignment armor_class armor_id body_parts challenge_rating cost discovery_dc experience hardness height hit_dice hit_points immunities is_magical languages length max_speed obj_type physiology_id psionics race reactions resistances senses skills spells states tags traits vulnerabilities weapon_categories weight width'.split(),
    },
    'being.BeingDictionary': {
        "allowed": 'object_categories objects'.split(),
        "required": 'object_categories objects'.split(),
    },
    'being.BeingInstance': {
        "allowed": '_atomic_target_history _skill_practice_baselines alignment current current_armor_class effective_fitness exertion fatigue_level front_facing geometry id name original parent_container_id personal_history physical_fatigue physiology_id possessions skill_experience skill_use_history spatial_state strategy top_facing type visual_occlusion weapons'.split(),
        "required": '_skill_practice_baselines current effective_fitness exertion fatigue_level front_facing geometry name original parent_container_id personal_history physical_fatigue physiology_id possessions skill_experience skill_use_history spatial_state strategy top_facing type visual_occlusion weapons'.split(),
    },
    'conditional_attributes.ConditionalAttributes': {
        "allowed": '_committed _external _rng_for specifications'.split(),
        "required": '_committed _external _rng_for specifications'.split(),
    },
    'encounter.Encounter': {
        "allowed": '_active_fatigue_frame _advancing _atomic_interval_history _boundary_context _choice_book _coordinator_time _dispatching _interval_start _physiology_registry _running _transactional_mode active_boundary awareness being_list boundary_fault cancelled_action_list difficulty_class end_time event_type fatigue_frame_history finished_action_list id initiated initiation last_fatigue_frame last_processed_boundary local_frame location map name non_being_object_list parent_event_id pending_action_list start_time time type universe'.split(),
        "required": '_active_fatigue_frame _advancing _boundary_context _choice_book _coordinator_time _dispatching _interval_start _physiology_registry _running active_boundary awareness boundary_fault cancelled_action_list difficulty_class end_time event_type fatigue_frame_history initiated last_fatigue_frame last_processed_boundary location map name parent_event_id start_time type universe'.split(),
    },
    'encounter.EncounterInitiation': {
        "allowed": 'actor_id intent target_id time'.split(),
        "required": 'actor_id intent target_id time'.split(),
    },
    'encounter_fatigue_bridge.FrozenFatigueFrame': {
        "allowed": '_profiles _views'.split(),
        "required": '_profiles _views'.split(),
    },
    'encounter_fatigue_bridge.FrozenFatigueView': {
        "allowed": 'b being_id check_modifier physiology_id q'.split(),
        "required": 'b being_id check_modifier physiology_id q'.split(),
    },
    'encounter_inspection.CommittedBoundaryRecord': {
        "allowed": 'action_anchors actions effects end entities objective objective_use participants recipients schedule start starts target_anchors'.split(),
        "required": 'action_anchors actions effects end entities objective objective_use participants recipients schedule start starts target_anchors'.split(),
    },
    'encounter_inspection.EntityInspection': {
        "allowed": 'category name obj_type position pre_action'.split(),
        "required": 'category name obj_type position pre_action'.split(),
    },
    'event.Event': {
        "allowed": 'end_time event_type id location name parent_event_id start_time type universe'.split(),
        "required": 'end_time event_type location name parent_event_id start_time type universe'.split(),
    },
    'exertion.Exertion': {
        "allowed": 'accumulated_exertion activity_level check_periods end_time fatigue_level fatigue_levels load_level start_time'.split(),
        "required": 'accumulated_exertion activity_level check_periods end_time fatigue_level fatigue_levels load_level start_time'.split(),
    },
    'experience.BatchSkillUse': {
        "allowed": 'action_id being_id exercises experience level_after level_before outcome skill_name time'.split(),
        "required": 'action_id being_id exercises experience level_after level_before outcome skill_name time'.split(),
    },
    'experience.SkillUse': {
        "allowed": 'action_id experience level_after level_before outcome skill_name time'.split(),
        "required": 'action_id experience level_after level_before outcome skill_name time'.split(),
    },
    'field_interpretation.FieldInterpretation': {
        "allowed": 'observation_id observer_id rejected_candidates reports skill_level skill_name'.split(),
        "required": 'observation_id observer_id rejected_candidates reports skill_level skill_name'.split(),
    },
    'field_interpretation.FieldInterpreter': {
        "allowed": 'expert_level skill_name'.split(),
        "required": 'expert_level skill_name'.split(),
    },
    'field_observation.BeliefLedger': {
        "allowed": '_belief_history _current_reassessments _evidence _inquiry_history _interpretations _reassessments communication_log observer_id'.split(),
        "required": '_belief_history _current_reassessments _evidence _inquiry_history _interpretations _reassessments communication_log observer_id'.split(),
    },
    'field_observation.BeliefRevision': {
        "allowed": 'category disputed estimate evidence_ids group_id time trigger trigger_observation_id'.split(),
        "required": 'category disputed estimate evidence_ids group_id time trigger trigger_observation_id'.split(),
    },
    'field_observation.CountReport': {
        "allowed": 'estimate uncertainty'.split(),
        "required": 'estimate uncertainty'.split(),
    },
    'field_observation.EvidenceReassessment': {
        "allowed": 'interpretation observation_id time'.split(),
        "required": 'interpretation observation_id time'.split(),
    },
    'field_observation.FieldObservation': {
        "allowed": 'dubious_candidates focus_category group_id id mode observer_id position_uncertainty_m reported_position reports time'.split(),
        "required": 'dubious_candidates focus_category group_id id mode observer_id position_uncertainty_m reported_position reports time'.split(),
    },
    'field_observation.InquiryProposal': {
        "allowed": 'category evidence_ids group_id observer_id reason time'.split(),
        "required": 'category evidence_ids group_id observer_id reason time'.split(),
    },
    'field_observation.InquiryRecord': {
        "allowed": 'action_id proposal'.split(),
        "required": 'action_id proposal'.split(),
    },
    'frozen_practice.CandidatePracticeUse': {
        "allowed": 'action_id effect_identity experience nominal_end outcome resolved_at skill_name'.split(),
        "required": 'action_id effect_identity experience nominal_end outcome resolved_at skill_name'.split(),
    },
    'frozen_practice.CandidateSkillTransition': {
        "allowed": 'baseline being_id effect_ids experience_after experience_before level_after level_before skill_name time'.split(),
        "required": 'baseline being_id effect_ids experience_after experience_before level_after level_before skill_name time'.split(),
    },
    'frozen_practice.PracticeProjection': {
        "allowed": 'baselines being_id exercises history_revision ordinary_levels prior_uses skill_experience transitions weapon_levels'.split(),
        "required": 'baselines being_id exercises history_revision ordinary_levels prior_uses skill_experience transitions weapon_levels'.split(),
    },
    'group_observation.ObserveGroupAction': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle _encounter actor_id canceled_at cancellation_reason end_time event_type experience_policy field_interpretation field_observation focus_category id instrument_id interpreter ledger location name observer parent_event_id random_key resolution roll seed skill_level_used start_time strategy target_id type universe'.split(),
        "required": '_encounter actor_id end_time event_type experience_policy field_interpretation field_observation focus_category instrument_id interpreter ledger location name observer parent_event_id random_key resolution roll seed skill_level_used start_time strategy target_id type universe'.split(),
    },
    'group_observation.SampledGroupObservation': {
        "allowed": 'coarse_range_m count_sigmas detailed_range_m focus_precision_factor max_ambiguous_dogs position_sigmas skill_precision_gain'.split(),
        "required": 'coarse_range_m count_sigmas detailed_range_m focus_precision_factor max_ambiguous_dogs position_sigmas skill_precision_gain'.split(),
    },
    'history_conversation.AskAboutPastAction': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle _encounter _pending_account actor_id canceled_at cancellation_reason end_time episode_time event_type generate heard_account id instrument_id location max_distance name newly_realized parent_event_id received_accounts resolution start_time strategy substituted_claim target_id topic type universe'.split(),
        "required": '_encounter _pending_account actor_id end_time episode_time event_type generate heard_account instrument_id location max_distance name newly_realized parent_event_id received_accounts resolution start_time strategy substituted_claim target_id topic type universe'.split(),
    },
    'history_conversation.HeardAccount': {
        "allowed": 'action_id claimed_time heard_at listener_id mode speaker_id topic words'.split(),
        "required": 'action_id claimed_time heard_at listener_id mode speaker_id topic words'.split(),
    },
    'interval_staging.AuthorityReference': {
        "allowed": 'identity key role'.split(),
        "required": 'identity key role'.split(),
    },
    'interval_staging.QueueProjection': {
        "allowed": 'action_states cancelled choice_states event_registrations finished pending reservations schedule_revision'.split(),
        "required": 'action_states cancelled choice_states event_registrations finished pending reservations schedule_revision'.split(),
    },
    'interval_staging.RegistrationIntent': {
        "allowed": 'accepted_packet action choice_id metadata signature_from_final_native_declaration'.split(),
        "required": 'accepted_packet action choice_id metadata signature_from_final_native_declaration'.split(),
    },
    'interval_staging.StartFence': {
        "allowed": 'metadata phase published_choices registered_action_ids started_action_ids time'.split(),
        "required": 'metadata phase published_choices registered_action_ids started_action_ids time'.split(),
    },
    'library.Library': {
        "allowed": 'action_dictionary armor_dictionary being_dictionary id name object_dictionary skill_dictionary type weapon_dictionary'.split(),
        "required": 'action_dictionary armor_dictionary being_dictionary name object_dictionary skill_dictionary type weapon_dictionary'.split(),
    },
    'melee_combat.MeleeStrike': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle _simultaneous_eligibility actor_id canceled_at cancellation_reason combat_result defended_by encounter end_time event_type hit_type id instrument_id location name parent_event_id reach resolution start_position start_time strategy target_id threat_at_schedule type universe'.split(),
        "required": '_simultaneous_eligibility actor_id combat_result defended_by encounter end_time event_type hit_type instrument_id location name parent_event_id reach resolution start_time strategy target_id type universe'.split(),
    },
    'melee_defense.MeleeDefense': {
        "allowed": '_activity_started _atomic_acknowledged_boundary _atomic_effect_ids _atomic_lifecycle actor_id canceled_at cancellation_reason defended_action_ids encounter end_time event_type id instrument_id kind location name parent_event_id ready_at resolution result start_position start_time strategy success target_action_id target_id threat_at_schedule type universe'.split(),
        "required": 'actor_id defended_action_ids encounter end_time event_type instrument_id kind location name parent_event_id ready_at resolution result start_time strategy success target_action_id target_id threat_at_schedule type universe'.split(),
    },
    'object.ObjectDefinition': {
        "allowed": 'cost discovery_dc hardness height hit_points is_magical length obj_type tags weapon_categories weight width'.split(),
        "required": 'cost discovery_dc hardness height hit_points is_magical length obj_type tags weapon_categories weight width'.split(),
    },
    'object.ObjectDictionary': {
        "allowed": 'object_categories objects'.split(),
        "required": 'object_categories objects'.split(),
    },
    'object.ObjectInstance': {
        "allowed": '_atomic_target_history current front_facing geometry id name original parent_container_id spatial_state top_facing type visual_occlusion'.split(),
        "required": 'current front_facing geometry name original parent_container_id spatial_state top_facing type visual_occlusion'.split(),
    },
    'object.ObjectRegistry': {
        "allowed": 'object_instances'.split(),
        "required": 'object_instances'.split(),
    },
    'objective_reality.DeclaredObjectiveFact': {
        "allowed": 'key origin value'.split(),
        "required": 'key origin value'.split(),
    },
    'objective_reality.EpisodeFacts': {
        "allowed": 'facts'.split(),
        "required": 'facts'.split(),
    },
    'objective_reality.ObjectiveFact': {
        "allowed": 'committed_revision established key origins requesting_action_ids supporting_keys value'.split(),
        "required": 'committed_revision established key origins requesting_action_ids supporting_keys value'.split(),
    },
    'objective_reality.SubjectRealityCandidate': {
        "allowed": 'base_revision counts facts ledger_identity subject_id'.split(),
        "required": 'base_revision counts facts ledger_identity subject_id'.split(),
    },
    'observer_proposals.AccountDeliveryEffect': {
        "allowed": 'account_id recipient source_action_id target_id'.split(),
        "required": 'account_id recipient source_action_id target_id'.split(),
    },
    'observer_proposals.AccountsProjection': {
        "allowed": 'accounts delivery_effect_ids identity'.split(),
        "required": 'accounts delivery_effect_ids identity'.split(),
    },
    'observer_proposals.ActionOutcomeEffect': {
        "allowed": 'action_id outcome source_action_id'.split(),
        "required": 'action_id outcome source_action_id'.split(),
    },
    'observer_proposals.BeliefAcquisitionEffect': {
        "allowed": 'acquired observation_id recipient source_action_id target_id'.split(),
        "required": 'acquired observation_id recipient source_action_id target_id'.split(),
    },
    'observer_proposals.BeliefProjection': {
        "allowed": 'auxiliary belief_history current_readings evidence identity interpretations observer_id'.split(),
        "required": 'auxiliary belief_history current_readings evidence identity interpretations observer_id'.split(),
    },
    'observer_proposals.InterpretationEffect': {
        "allowed": 'observation_id source_action_id target_id'.split(),
        "required": 'observation_id source_action_id target_id'.split(),
    },
    'observer_proposals.LifecycleEffect': {
        "allowed": 'action_id boundary canceled_at cancellation_reason choice_id from_queue nominal_end previous_choice_action_state source_action_id status to_queue'.split(),
        "required": 'action_id boundary canceled_at cancellation_reason choice_id from_queue nominal_end previous_choice_action_state source_action_id status to_queue'.split(),
    },
    'observer_proposals.ObjectiveUse': {
        "allowed": 'constructed consumed_by eligible_new_fact key requested_by subject_id'.split(),
        "required": 'constructed consumed_by eligible_new_fact key requested_by subject_id'.split(),
    },
    'observer_proposals.ObservationEffect': {
        "allowed": 'observation_id source_action_id target_id'.split(),
        "required": 'observation_id source_action_id target_id'.split(),
    },
    'observer_proposals.ObserverProjection': {
        "allowed": 'belief_recipient_ids heard_accounts interpretations observations observer_id'.split(),
        "required": 'belief_recipient_ids heard_accounts interpretations observations observer_id'.split(),
    },
    'observer_proposals.PostCommitNotificationIntent': {
        "allowed": 'action_id after_commit source_action_id topic'.split(),
        "required": 'action_id after_commit source_action_id topic'.split(),
    },
    'observer_proposals.RecipientIdentity': {
        "allowed": 'object_identity role'.split(),
        "required": 'object_identity role'.split(),
    },
    'observer_proposals.ReservationReleaseEffect': {
        "allowed": 'action_id after_settlement choice_id not_before_boundary object_id source_action_id'.split(),
        "required": 'action_id after_settlement choice_id not_before_boundary object_id source_action_id'.split(),
    },
    'observer_proposals.TestimonyEffect': {
        "allowed": 'account_id source_action_id target_id'.split(),
        "required": 'account_id source_action_id target_id'.split(),
    },
    'personal_history.PersonalHistory': {
        "allowed": 'being earliest known_through nondeclining_skills reality'.split(),
        "required": 'being earliest known_through nondeclining_skills reality'.split(),
    },
    'physical_fatigue.PhysicalFatigueState': {
        "allowed": 'b q'.split(),
        "required": 'b q'.split(),
    },
    'physiology_registry.PhysiologyDefinition': {
        "allowed": 'identifier model parameters parent_id'.split(),
        "required": 'identifier model parameters parent_id'.split(),
    },
    'physiology_registry.PhysiologyRegistry': {
        "allowed": '_definitions'.split(),
        "required": '_definitions'.split(),
    },
    'physiology_registry.ResolvedPhysiology': {
        "allowed": 'identifier lineage mode profile version_hash'.split(),
        "required": 'identifier lineage mode profile version_hash'.split(),
    },
    'realization.CommittedFact': {
        "allowed": 'key origin revision value'.split(),
        "required": 'key origin revision value'.split(),
    },
    'realization.Fact': {
        "allowed": 'key origin value'.split(),
        "required": 'key origin value'.split(),
    },
    'realization.FactKey': {
        "allowed": 'attribute detail entity_id time'.split(),
        "required": 'attribute detail entity_id time'.split(),
    },
    'realization.RealityLedger': {
        "allowed": '_atomic_provenance _records _revision _validators'.split(),
        "required": '_records _revision _validators'.split(),
    },
    'scheduling.PreparedSchedule': {
        "allowed": 'action_id active_object_ids actor_id end_time initialization instrument_id parent_event_id start_time target_id'.split(),
        "required": 'action_id active_object_ids actor_id end_time initialization instrument_id parent_event_id start_time target_id'.split(),
    },
    'skill.SkillDefinition': {
        "allowed": 'is_ordinary is_progressive name'.split(),
        "required": 'is_ordinary is_progressive name'.split(),
    },
    'skill.SkillDictionary': {
        "allowed": 'skills'.split(),
        "required": 'skills'.split(),
    },
    'skill.Skills': {
        "allowed": 'skills weapon_skills'.split(),
        "required": 'skills weapon_skills'.split(),
    },
    'spatial.frame.LocalFrame': {
        "allowed": 'origin x_axis y_axis z_axis'.split(),
        "required": 'origin x_axis y_axis z_axis'.split(),
    },
    'spatial.geometry.AxisAlignedBox': {
        "allowed": 'size_x size_y size_z'.split(),
        "required": 'size_x size_y size_z'.split(),
    },
    'spatial.geometry.Sphere': {
        "allowed": 'radius'.split(),
        "required": 'radius'.split(),
    },
    'spatial.occlusion.VisualOcclusion': {
        "allowed": 'opacity'.split(),
        "required": 'opacity'.split(),
    },
    'spatial.state.CartesianPosition': {
        "allowed": 'x y z'.split(),
        "required": 'x y z'.split(),
    },
    'spatial.state.SpatialState': {
        "allowed": 'position'.split(),
        "required": 'position'.split(),
    },
    'speeds.Speed': {
        "allowed": 'speeds'.split(),
        "required": 'speeds'.split(),
    },
    'states.States': {
        "allowed": 'states'.split(),
        "required": 'states'.split(),
    },
    'statistical_group.StatisticalGroup': {
        "allowed": '_atomic_target_history _composition_reality _conditional_attributes _counts _departed_member_ids _formation_traits _incoming_beings _members _motion_attached_native_ids _realized_beings acceleration config current footprint_radius formation_time front_facing geometry id max_acceleration membership_history name original parent_container_id seed spatial_state time top_facing type velocity visual_occlusion'.split(),
        "required": '_composition_reality _conditional_attributes _counts _departed_member_ids _formation_traits _incoming_beings _members _motion_attached_native_ids _realized_beings acceleration config current footprint_radius formation_time front_facing geometry max_acceleration membership_history name original parent_container_id seed spatial_state time top_facing type velocity visual_occlusion'.split(),
    },
    'strategy.Strategy': {
        "allowed": 'attack defense extra_damage timing'.split(),
        "required": 'attack defense extra_damage timing'.split(),
    },
    'universe.Universe': {
        "allowed": '_choice_books _schedule_lock _schedule_revision event_history id library name object_registry type'.split(),
        "required": '_choice_books _schedule_lock _schedule_revision event_history library name object_registry type'.split(),
    },
    'universe_physical_fatigue_r4.Profile': {
        "allowed": 'critical_floor critical_fresh fast_budget fast_recovery peak_curve peak_floor slow_baseline slow_depletion slow_recovery_awake slow_recovery_sleep'.split(),
        "required": 'critical_floor critical_fresh fast_budget fast_recovery peak_curve peak_floor slow_baseline slow_depletion slow_recovery_awake slow_recovery_sleep'.split(),
    },
    'weapon.WeaponDefinition': {
        "allowed": 'attacks cost discovery_dc hardness height hit_points is_magical length obj_type tags weapon_categories weapon_size weight width'.split(),
        "required": 'attacks cost discovery_dc hardness height hit_points is_magical length obj_type tags weapon_categories weapon_size weight width'.split(),
    },
    'weapon.WeaponDictionary': {
        "allowed": 'object_categories objects'.split(),
        "required": 'object_categories objects'.split(),
    },
    'weapon.WeaponInstance': {
        "allowed": '_atomic_target_history current front_facing geometry id name original parent_container_id spatial_state top_facing type visual_occlusion'.split(),
        "required": 'current front_facing geometry name original parent_container_id spatial_state top_facing type visual_occlusion'.split(),
    },
}

# Semantic scope certified by 5D2C3.  FIELD_ADAPTERS supplies the reviewed
# closed field vocabulary; this table adds role-specific treatment for the
# native Run/Spot dependency graph.  It deliberately does not claim closure
# for unrelated Library dictionaries or checkpoint reconstruction.
RUN_SPOT_FIELD_CLOSURE = {
    'universe.Universe': {
        'authoritative': ('id', 'name', 'library', 'object_registry', 'event_history',
                          '_schedule_revision', '_choice_books'),
        'derived': ('type',),
        'transient': ('_schedule_lock',),
    },
    'library.Library': {
        'authoritative': ('id', 'name', 'being_dictionary', 'skill_dictionary'),
        'derived': ('type',),
        'out_of_scope': ('action_dictionary', 'armor_dictionary',
                         'object_dictionary', 'weapon_dictionary'),
    },
    'being.BeingDictionary': {
        'authoritative': ('objects',),
        'derived': (),
        'out_of_scope': ('object_categories',),
    },
    'skill.SkillDictionary': {
        'authoritative': ('skills',),
        'derived': (),
        'entry_schema': ('exact-dict', ('is_ordinary', 'is_progressive'),
                         ('bool', 'bool')),
    },
    'being.BeingInstance': {
        'authoritative': ('id', 'name', 'original', 'current', 'parent_container_id',
                          'top_facing', 'front_facing', 'spatial_state', 'geometry',
                          'visual_occlusion', 'possessions', 'weapons', 'strategy',
                          'physical_fatigue', 'physiology_id', 'fatigue_level',
                          'effective_fitness', 'exertion', 'skill_experience',
                          'skill_use_history', '_skill_practice_baselines',
                          'personal_history', '_atomic_target_history'),
        'derived': ('type',),
        'optional_values': {
            'spatial_state': ('null', 'spatial.SpatialState'),
            'geometry': ('null', 'spatial.geometry.Sphere',
                         'spatial.geometry.AxisAlignedBox'),
            'visual_occlusion': ('null', 'spatial.occlusion.VisualOcclusion'),
            '_atomic_target_history': ('absent-before-first-commit',
                                       'list-matching-receipts'),
            'physiology_id': ('null', 'registered PhysiologyRegistry ID'),
            'personal_history': ('null-only-in-this-subset',),
        },
        'unsupported_optional': ('alignment', 'current_armor_class'),
    },
    'being.BeingDefinition': {
        'authoritative': ('obj_type', 'length', 'width', 'height', 'weight',
                          'cost', 'hardness', 'hit_points', 'is_magical',
                          'tags', 'weapon_categories', 'experience',
                          'hit_dice', 'alignment', 'armor_class',
                          'challenge_rating', 'max_speed', 'abilities',
                          'skills', 'senses', 'vulnerabilities', 'resistances',
                          'immunities', 'languages', 'psionics', 'spells',
                          'traits', 'states', 'actions', 'reactions',
                          'body_parts', 'armor_id', 'physiology_id', 'race',
                          'discovery_dc'),
        'derived': (),
    },
}
