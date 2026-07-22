<template>
	<div
		v-if="!resource"
		class="flex h-full flex-col items-center justify-center gap-2 p-8 text-sm text-ink-gray-5"
	>
		<div>Unknown resource: {{ resourceKey || "(empty)" }}</div>
		<Button label="Dashboard" @click="$router.push('/dashboard')" />
	</div>
	<div v-else class="flex h-full flex-col overflow-hidden">
		<LayoutHeader>
			<template #left-header>
				<div class="flex min-w-0 items-center gap-1.5">
					<PageBreadcrumbs
						:parent="resource.title"
						:parent-route="`/${resource.route}`"
						current="List"
						:view-options="[
							{
								group: 'Views',
								hideLabel: true,
								items: [{ label: 'List', onClick: () => goList() }],
							},
						]"
					/>
					<span class="mx-0.5 text-base text-ink-gray-4" aria-hidden="true">/</span>
					<span class="truncate text-lg font-medium text-ink-gray-9">
						{{ isNew ? "New" : doc?.name || "—" }}
					</span>
				</div>
			</template>
			<template #right-header>
				<div class="flex flex-wrap items-center justify-end gap-2">
					<AssignTo
						v-if="!isNew && doc?.name"
						:doctype="resource.doctype"
						:docname="doc.name"
					/>
					<Badge
						v-if="showDocstatusBadge"
						:label="docstatusLabel"
						:theme="docstatusTheme"
						variant="subtle"
					/>
					<select
						v-if="canEditVisitStatus"
						class="rounded-full border border-outline-gray-2 bg-surface-gray-2 px-2.5 py-1 text-sm font-medium text-ink-gray-8"
						:value="doc?.status || ''"
						@change="onVisitStatusChange($event)"
					>
						<option v-for="opt in visitStatusOptions" :key="opt" :value="opt">
							{{ opt }}
						</option>
					</select>
					<span
						v-else-if="showOpsStatus"
						class="inline-flex items-center gap-1.5 rounded-full bg-surface-gray-2 px-2.5 py-1 text-sm font-medium text-ink-gray-8"
					>
						<IndicatorIcon :class="parseStatusColor(statusValue)" />
						{{ statusValue }}
					</span>
					<!-- Desk-standard: secondary then primary -->
					<Button
						v-if="secondaryAction"
						variant="outline"
						:label="secondaryAction.label"
						:theme="secondaryAction.theme || 'gray'"
						:loading="saving && ['Cancel', 'Save'].includes(secondaryAction.label)"
						:disabled="saving"
						@click="secondaryAction.run()"
					/>
					<Button
						v-if="primaryAction"
						variant="solid"
						:label="primaryAction.label"
						:loading="saving"
						:disabled="!!primaryAction.disabled || saving"
						:title="primaryAction.title || undefined"
						@click="primaryAction.run()"
					/>
				</div>
			</template>
		</LayoutHeader>

		<div v-if="loading" class="flex flex-1 items-center justify-center text-sm text-ink-gray-5">
			Loading...
		</div>

		<div v-else-if="error && !doc" class="flex flex-1 flex-col items-center justify-center gap-3 p-8">
			<ErrorMessage :message="error" />
			<Button label="Back to list" @click="goList" />
		</div>

		<div v-else-if="doc" class="flex min-h-0 flex-1 overflow-hidden">
			<!-- Main tabs (CRM style) -->
			<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
				<Alert
					v-if="isCancelled"
					class="mx-5 mt-3"
					title="Document cancelled"
					theme="red"
					:description="cancelledAlertDescription"
				/>
				<div v-if="isCancelled && amendmentName" class="mx-5 mt-2">
					<Button
						variant="solid"
						:label="`Open amendment ${amendmentName}`"
						@click="router.push(`/${resource.route}/${encodeURIComponent(amendmentName)}`)"
					/>
				</div>
				<Alert
					v-else-if="isSubmitted"
					class="mx-5 mt-3"
					title="Document submitted"
					theme="blue"
					description="Only allow-on-submit fields can be edited. Use Update to save, or Cancel to reverse."
				/>
				<ErrorMessage class="mx-5 mt-2" :message="error" />

				<div
					v-if="resource.process === 'service-request' && !isNew && formTab === 0"
					class="mx-5 mt-3"
				>
					<Progress
						label="Lifecycle"
						:value="lifecycleProgress"
						size="sm"
					/>
					<div class="mt-1 text-sm text-ink-gray-6">{{ lifecycleHint }}</div>
				</div>

				<Tabs
					v-model="formTab"
					as="div"
					:tabs="formTabs"
					class="flex min-h-0 flex-1 flex-col overflow-hidden [&_[role='tablist']]:min-h-[45px] [&_[role='tablist']]:gap-7.5 [&_[role='tablist']]:px-5 [&_[role='tablist']::-webkit-scrollbar]:h-0 [&_[role='tabpanel']:not([hidden])]:flex [&_[role='tabpanel']:not([hidden])]:min-h-0 [&_[role='tabpanel']:not([hidden])]:flex-1 [&_[role='tabpanel']:not([hidden])]:flex-col"
				>
					<template #tab-item="{ tab, selected }">
						<button
							type="button"
							class="group flex items-center gap-2 border-b border-transparent py-2.5 text-base text-ink-gray-5 duration-300 ease-in-out hover:text-ink-gray-9"
							:class="{ '!border-ink-gray-9 text-ink-gray-9': selected }"
						>
							<component :is="tab.icon" v-if="tab.icon" class="size-5 shrink-0" />
							{{ tab.label }}
						</button>
					</template>
					<template #tab-panel="{ tab }">
						<div
							v-if="formTabs[formTab]?.label === tab.label"
							class="min-h-0 flex-1 overflow-auto px-5 py-5"
						>
							<template v-if="tab.label === 'Details'">
								<FormFields
									:fields="formFields"
									:model="doc"
									:disabled="isCancelled"
									:submitted="isSubmitted"
									size="md"
								/>
							</template>
							<template v-else-if="tab.label === 'GPS'">
								<div class="w-full rounded-xl border border-outline-gray-2 bg-surface-white p-4 sm:p-5">
									<VisitGpsPanel :doc="doc" full-width @updated="onGpsUpdated" />
								</div>
							</template>
							<template v-else-if="tab.label === 'Connections'">
								<DocConnections
									v-if="doc?.name"
									ref="connectionsRef"
									:doctype="resource.doctype"
									:name="doc.name"
								/>
							</template>
							<template v-else-if="tab.label === 'Activity'">
								<DocActivity
									v-if="doc?.name && !isNew"
									:doctype="resource.doctype"
									:name="doc.name"
								/>
								<div
									v-else
									class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
								>
									Save the document to see activity.
								</div>
							</template>
							<template v-else-if="tab.label === 'Emails'">
								<DocEmails
									v-if="doc?.name && !isNew"
									:doctype="resource.doctype"
									:name="doc.name"
									:default-subject="emailSubject"
								/>
								<div
									v-else
									class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
								>
									Save the document to send emails.
								</div>
							</template>
							<template v-else-if="tab.label === 'Comments'">
								<DocComments
									v-if="doc?.name && !isNew"
									:doctype="resource.doctype"
									:name="doc.name"
								/>
								<div
									v-else
									class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
								>
									Save the document to add comments.
								</div>
							</template>
							<template v-else-if="tab.label === 'Data'">
								<div class="overflow-hidden rounded-lg border border-outline-gray-2">
									<table class="w-full text-left text-sm">
										<tbody>
											<tr
												v-for="row in dataTabRows"
												:key="row.label"
												class="border-b border-outline-gray-1 last:border-0"
											>
												<th class="w-48 bg-surface-gray-1 px-4 py-2.5 font-medium text-ink-gray-6">
													{{ row.label }}
												</th>
												<td class="px-4 py-2.5 text-ink-gray-9">
													{{ row.value ?? "—" }}
												</td>
											</tr>
										</tbody>
									</table>
								</div>
							</template>
							<template v-else-if="tab.label === 'Notes'">
								<DocNotes
									v-if="doc?.name && !isNew"
									:doctype="resource.doctype"
									:name="doc.name"
								/>
								<div
									v-else
									class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
								>
									Save the document to add notes.
								</div>
							</template>
							<template v-else-if="tab.label === 'Attachments'">
								<DocAttachments
									v-if="doc?.name && !isNew"
									:doctype="resource.doctype"
									:name="doc.name"
								/>
								<div
									v-else
									class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
								>
									Save the document to upload attachments.
								</div>
							</template>
						</div>
					</template>
				</Tabs>
			</div>

			<!-- Right rail (CRM style) -->
			<Resizer
				v-if="!isNew && doc?.name"
				class="hidden h-full shrink-0 lg:flex lg:flex-col"
				side="right"
				:default-width="352"
			>
				<DocSidePanel
					:doc="doc"
					:docname="doc.name"
					:title-field="resource.titleField || 'subject'"
					:status-field="resource.statusField || 'status'"
					:fields="formFields"
					:docstatus-label="showDocstatusBadge ? docstatusLabel : ''"
					@print="doPrint"
				>
					<!-- Process actions -->
					<section v-if="workflow.has_workflow" class="mb-5">
						<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
							Workflow
						</div>
						<div class="mb-2 text-sm text-ink-gray-6">
							{{ workflow.workflow_state || "—" }}
						</div>
						<div class="flex flex-col gap-1.5">
							<Button
								v-for="t in workflow.transitions || []"
								:key="t.action"
								variant="solid"
								class="w-full justify-start"
								:label="t.action"
								:loading="saving"
								@click="runWorkflow(t.action)"
							/>
						</div>
					</section>

					<template v-if="resource.process === 'service-request' && !isCancelled && !isNew">
						<section v-if="canAssignEngineer" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Assignment
							</div>
							<Button
								variant="outline"
								class="w-full justify-start"
								label="Assign Engineer & Plan Visit"
								iconLeft="lucide-user-plus"
								@click="showAssign = true"
							/>
						</section>
						<section v-if="canAdvanceVisit" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Visit
							</div>
							<div class="flex flex-col gap-1.5">
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Advance Status"
									iconLeft="lucide-chevrons-right"
									@click="advanceStatus"
								/>
							</div>
						</section>
						<section v-if="canDiagnose" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Diagnosis
							</div>
							<Button
								variant="solid"
								class="w-full justify-start"
								label="Apply Diagnosis"
								@click="applyDiagnosis"
							/>
						</section>
						<section v-if="canBranchOutcomes" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Next steps
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="ghost" class="w-full justify-start" label="Spare Request" iconLeft="lucide-wrench" @click="createSpare" />
								<Button variant="ghost" class="w-full justify-start" label="Factory RMA" iconLeft="lucide-factory" @click="createRma" />
								<Button variant="ghost" class="w-full justify-start" label="Replacement" iconLeft="lucide-repeat-2" @click="createReplacement" />
								<Button variant="ghost" class="w-full justify-start" label="Billing" iconLeft="lucide-receipt" @click="createEstimate" />
							</div>
						</section>
						<section v-if="canCloseOut">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Closure
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="ghost" class="w-full justify-start" label="Generate Service Report" iconLeft="lucide-file-text" @click="generateReportFromSSR" />
								<Button variant="ghost" class="w-full justify-start" label="Feedback" iconLeft="lucide-message-square" @click="createFeedback" />
								<Button variant="solid" class="w-full justify-start" label="Generate Service Closure" iconLeft="lucide-badge-check" @click="generateClosureFromSSR" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'engineer-assignment' && !isCancelled && !isNew">
						<section v-if="canAcceptAssignment" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Response
							</div>
							<div class="flex flex-col gap-1.5">
								<Button
									variant="solid"
									class="w-full justify-start"
									label="Accept Assignment"
									iconLeft="lucide-check"
									@click="acceptAssignment"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Reject Assignment"
									iconLeft="lucide-x"
									@click="rejectAssignment"
								/>
							</div>
						</section>
						<section v-if="canAdvanceAssignment" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Lifecycle
							</div>
							<Button
								variant="outline"
								class="w-full justify-start"
								label="Advance Status"
								iconLeft="lucide-chevrons-right"
								@click="advanceAssignment"
							/>
						</section>
						<section v-if="doc?.engineer_visit" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Visit
							</div>
							<Button
								variant="ghost"
								class="w-full justify-start"
								label="Open Engineer Visit"
								iconLeft="lucide-map-pin"
								@click="router.push(`/engineer-visits/${encodeURIComponent(doc.engineer_visit)}`)"
							/>
						</section>
						<section v-if="canSuggestEngineers" class="mb-5">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Suggestions
							</div>
							<Button
								variant="ghost"
								class="w-full justify-start"
								label="Suggest Engineers"
								iconLeft="lucide-sparkles"
								@click="loadEngineerSuggestions"
							/>
							<div v-if="engineerSuggestions.length" class="mt-2 space-y-1.5">
								<button
									v-for="s in engineerSuggestions"
									:key="s.engineer"
									type="button"
									class="w-full rounded-md border border-outline-gray-2 px-2 py-1.5 text-left text-sm hover:bg-surface-gray-2"
									@click="applySuggestedEngineer(s)"
								>
									<div class="font-medium text-ink-gray-9">{{ s.full_name || s.engineer }}</div>
									<div class="text-xs text-ink-gray-5">
										Score {{ s.score }} · load {{ s.workload }}/{{ s.max_open_jobs }}
									</div>
								</button>
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'visit'">
						<section class="mb-4">
							<VisitGpsPanel :doc="doc" @updated="onGpsUpdated" />
						</section>
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Service Visit
							</div>
							<div class="flex flex-col gap-1.5">
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Advance Status"
									@click="advanceVisit"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Open Diagnosis / RCA"
									@click="openDiagnosisFromVisit"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Create Spare Request"
									@click="createSpareFromVisit"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Create Repair Order"
									@click="createRepairFromVisit"
								/>
								<Button
									variant="solid"
									class="w-full justify-start"
									label="Generate Service Report"
									@click="generateReportFromVisit"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Create Follow-up Visit"
									iconLeft="lucide-calendar-plus"
									@click="createFollowUpVisit"
								/>
							</div>
						</section>
						<section class="mt-4">
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Outcome
							</div>
							<div class="flex flex-col gap-1.5">
								<Button
									v-for="o in visitOutcomes"
									:key="o"
									variant="ghost"
									class="w-full justify-start"
									:label="o"
									@click="setVisitOutcome(o)"
								/>
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'diagnosis'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Diagnosis / RCA
							</div>
							<div class="flex flex-col gap-1.5">
								<Button
									variant="solid"
									class="w-full justify-start"
									label="Advance Status"
									@click="advanceDiagnosis"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Create Spare Request"
									@click="createSpareFromDiagnosis"
								/>
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Create Repair Order"
									@click="createRepairFromDiagnosis"
								/>
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'spare'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Spare Fulfillment
							</div>
							<div class="flex flex-col gap-1.5">
								<Button
									variant="outline"
									class="w-full justify-start"
									label="Advance / Next Step"
									@click="advanceSpare"
								/>
								<Button variant="solid" class="w-full justify-start" label="Approve & Reserve" @click="approveSpare" />
								<Button variant="outline" class="w-full justify-start" label="Issue Parts" @click="issueSpare" />
								<Button variant="outline" class="w-full justify-start" label="Engineer Received" @click="receiveSpare" />
								<Button variant="outline" class="w-full justify-start" label="Mark Consumed" @click="consumeSpare" />
								<Button variant="ghost" class="w-full justify-start" label="Create Purchase Request" @click="createSpareMR" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'repair'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Workshop Repair
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="outline" class="w-full justify-start" label="Advance Status" @click="advanceRepair" />
								<Button variant="solid" class="w-full justify-start" label="Mark Received" @click="repairReceived" />
								<Button variant="outline" class="w-full justify-start" label="Start Repair" @click="repairStart" />
								<Button variant="outline" class="w-full justify-start" label="Complete Repair" @click="repairComplete" />
								<Button variant="outline" class="w-full justify-start" label="Pass Testing" @click="repairPassTesting" />
								<Button variant="outline" class="w-full justify-start" label="QI Pass" @click="repairPassQuality" />
								<Button variant="outline" class="w-full justify-start" label="Dispatch" @click="repairDispatch" />
								<Button variant="ghost" class="w-full justify-start" label="Recommend Replacement" @click="repairRecommendReplacement" />
								<Button variant="solid" class="w-full justify-start" label="Generate Service Report" @click="generateReportFromRepair" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'service-report'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Service Report
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="outline" class="w-full justify-start" label="Advance Status" @click="advanceServiceReport" />
								<Button variant="solid" class="w-full justify-start" label="Engineer Review" @click="srptEngineerReview" />
								<Button variant="outline" class="w-full justify-start" label="Mark Customer Signed" @click="srptCustomerSign" />
								<Button variant="outline" class="w-full justify-start" label="Manager Verify" @click="srptManagerVerify" />
								<Button variant="outline" class="w-full justify-start" label="Billing Ready" @click="srptBillingReady" />
								<Button variant="outline" class="w-full justify-start" label="Create Billing" @click="generateBillingFromReport" />
								<Button variant="solid" class="w-full justify-start" label="Request Feedback" @click="generateFeedbackFromReport" />
								<Button variant="ghost" class="w-full justify-start" label="Create Revision" @click="srptCreateRevision" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'feedback'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								CSAT &amp; NPS
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="outline" class="w-full justify-start" label="Advance Status" @click="advanceFeedback" />
								<Button variant="solid" class="w-full justify-start" label="Request Feedback" @click="feedbackRequest" />
								<Button variant="outline" class="w-full justify-start" label="Record Response" @click="feedbackSubmitResponse" />
								<Button variant="outline" class="w-full justify-start" label="Mark Reviewed" @click="feedbackReview" />
								<Button variant="outline" class="w-full justify-start" label="Resolve Escalation" @click="feedbackResolveEscalation" />
								<Button variant="ghost" class="w-full justify-start" label="Close Feedback" @click="feedbackClose" />
								<Button variant="solid" class="w-full justify-start" label="Generate Service Closure" @click="generateClosureFromFeedback" />
								<Button variant="ghost" class="w-full justify-start" label="Create Revision" @click="feedbackCreateRevision" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'closure'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Governance Closure
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="outline" class="w-full justify-start" label="Advance Status" @click="advanceClosure" />
								<Button variant="solid" class="w-full justify-start" label="Run Validation" @click="closureRunValidation" />
								<Button variant="outline" class="w-full justify-start" label="Approve Closure" @click="closureApprove" />
								<Button variant="solid" class="w-full justify-start" label="Execute Close" @click="closureExecuteClose" />
								<Button variant="ghost" class="w-full justify-start" label="Archive" @click="closureArchive" />
								<Button variant="outline" class="w-full justify-start" label="Request Reopen" @click="closureRequestReopen" />
								<Button variant="ghost" class="w-full justify-start" label="Approve Reopen" @click="closureApproveReopen" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'billing'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Commercial Settlement
							</div>
							<div class="flex flex-col gap-1.5">
								<Button variant="outline" class="w-full justify-start" label="Advance Status" @click="advanceBilling" />
								<Button variant="solid" class="w-full justify-start" label="Approve" @click="billingApprove" />
								<Button variant="outline" class="w-full justify-start" label="Generate Invoice" @click="billingGenerateInvoice" />
								<Button variant="outline" class="w-full justify-start" label="Record Payment" @click="billingRecordPayment" />
								<Button variant="ghost" class="w-full justify-start" label="Warranty Settle" @click="billingWarrantySettle" />
								<Button variant="ghost" class="w-full justify-start" label="Credit Note" @click="billingCreditNote" />
								<Button variant="solid" class="w-full justify-start" label="Request Feedback" @click="generateFeedbackFromBilling" />
							</div>
						</section>
					</template>

					<template v-else-if="resource.process === 'estimate'">
						<section>
							<div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
								Billing
							</div>
							<Button variant="solid" class="w-full justify-start" label="Create Sales Invoice" @click="createInvoice" />
						</section>
					</template>
				</DocSidePanel>
			</Resizer>
		</div>

		<!-- Mobile sticky GPS / actions (phones) -->
		<div
			v-if="doc && !isNew"
			class="shrink-0 border-t border-outline-gray-2 bg-surface-white p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] lg:hidden"
		>
			<template v-if="resource.process === 'visit'">
				<div class="grid grid-cols-2 gap-2">
					<Button
						variant="solid"
						label="Check-in"
						iconLeft="lucide-map-pin"
						class="w-full"
						:loading="saving"
						@click="mobileCheckIn"
					/>
					<Button
						variant="outline"
						label="Check-out"
						iconLeft="lucide-log-out"
						class="w-full"
						:loading="saving"
						@click="mobileCheckOut"
					/>
				</div>
				<div class="mt-2 grid grid-cols-2 gap-2">
					<Button variant="outline" label="Advance" class="w-full" @click="advanceVisit" />
					<Button variant="solid" label="Report" class="w-full" @click="generateReportFromVisit" />
				</div>
			</template>
			<template v-else-if="hasActions">
				<Button
					variant="solid"
					class="w-full"
					label="Process actions"
					iconLeft="lucide-zap"
					@click="showMobileActions = true"
				/>
			</template>
		</div>

		<Dialog v-model="showMobileActions" :options="{ title: 'Actions', size: 'md' }">
			<template #body-content>
				<div class="flex max-h-[60vh] flex-col gap-2 overflow-y-auto">
					<template v-if="resource.process === 'service-request'">
						<Button
							v-if="canAssignEngineer"
							variant="solid"
							label="Assign Engineer"
							class="w-full justify-start"
							@click="
								showMobileActions = false;
								showAssign = true;
							"
						/>
						<Button
							v-if="canAdvanceVisit"
							variant="outline"
							label="Advance status"
							class="w-full justify-start"
							@click="
								showMobileActions = false;
								advanceStatus();
							"
						/>
					</template>
					<template v-else>
						<p class="text-p-sm text-ink-gray-5">
							Use the Details tab for process steps on this document.
						</p>
					</template>
				</div>
			</template>
		</Dialog>

		<Dialog v-model="showAssign" :options="{ title: 'Assign Engineer', size: 'md' }">
			<template #body-content>
				<FormFields
					:fields="[
						{ fieldname: 'engineer', label: 'Engineer', fieldtype: 'Link', options: 'User', reqd: 1 },
						{ fieldname: 'visit_date', label: 'Visit Date', fieldtype: 'Date' },
					]"
					:model="assignForm"
				/>
			</template>
			<template #actions>
				<Button class="w-full" variant="solid" label="Assign" :loading="saving" @click="doAssign" />
			</template>
		</Dialog>

		<Dialog v-model="showSpare" :options="{ title: 'Create Spare Request', size: 'md' }">
			<template #body-content>
				<FormFields
					:fields="[
						{ fieldname: 'item_code', label: 'Item', fieldtype: 'Link', options: 'Item', reqd: 1 },
						{ fieldname: 'qty', label: 'Qty', fieldtype: 'Float', default: 1 },
						{ fieldname: 'warehouse', label: 'Warehouse', fieldtype: 'Link', options: 'Warehouse' },
					]"
					:model="spareForm"
				/>
			</template>
			<template #actions>
				<Button class="w-full" variant="solid" label="Create" :loading="saving" @click="doCreateSpare" />
			</template>
		</Dialog>

		<Dialog v-model="showReport" :options="{ title: 'Create Service Report', size: 'md' }">
			<template #body-content>
				<FormFields
					:fields="[
						{ fieldname: 'work_done', label: 'Work Done', fieldtype: 'Text', reqd: 1, col: 'sm:col-span-2' },
					]"
					:model="reportForm"
				/>
			</template>
			<template #actions>
				<Button class="w-full" variant="solid" label="Create" :loading="saving" @click="doCreateReport" />
			</template>
		</Dialog>

		<QuickEditModal
			v-if="showQuickEdit && doc?.name"
			v-model="showQuickEdit"
			:title="`Quick Edit — ${doc.name}`"
			:doctype="resource.doctype"
			:fields="resource.createFields?.length ? resource.createFields : (resource.formFields || []).slice(0, 8)"
			:doc="doc"
			@saved="onQuickSaved"
		/>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Alert,
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	Progress,
	Tabs,
	call,
	confirmDialog,
	toast,
} from "frappe-ui";
import { useOnboarding } from "frappe-ui/frappe";
import LucideFileText from "~icons/lucide/file-text";
import LucideLink2 from "~icons/lucide/link-2";
import LucideActivity from "~icons/lucide/activity";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideMail from "~icons/lucide/mail";
import LucideList from "~icons/lucide/list";
import LucideStickyNote from "~icons/lucide/sticky-note";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideLayoutGrid from "~icons/lucide/layout-grid";
import LucideMapPin from "~icons/lucide/map-pin";
import LayoutHeader from "@/components/LayoutHeader.vue";
import PageBreadcrumbs from "@/components/PageBreadcrumbs.vue";
import FormFields from "@/components/FormFields.vue";
import AssignTo from "@/components/AssignTo.vue";
import QuickEditModal from "@/components/QuickEditModal.vue";
import DocConnections from "@/components/DocConnections.vue";
import DocActivity from "@/components/DocActivity.vue";
import DocComments from "@/components/DocComments.vue";
import DocNotes from "@/components/DocNotes.vue";
import DocEmails from "@/components/DocEmails.vue";
import DocAttachments from "@/components/DocAttachments.vue";
import DocSidePanel from "@/components/DocSidePanel.vue";
import VisitGpsPanel from "@/components/VisitGpsPanel.vue";
import Resizer from "@/components/Resizer.vue";
import IndicatorIcon from "@/components/Icons/IndicatorIcon.vue";
import { getResourceByRoute } from "@/config/resources";
import { ONBOARDING_APP, resourceOnboardingMap } from "@/config/onboarding";
import { parseStatusColor } from "@/utils/format";
import { openPrintView } from "@/utils/frappeDocs";

const props = defineProps({
	resourceKey: { type: String, default: "" },
});

const route = useRoute();
const router = useRouter();
const resourceKey = computed(() => props.resourceKey || route.meta.resourceKey || "");
const resource = computed(() => getResourceByRoute(resourceKey.value));
const onboarding = useOnboarding(ONBOARDING_APP);
const updateOnboardingStep = onboarding?.updateOnboardingStep || (() => {});

function markOnboarding(step) {
	try {
		updateOnboardingStep(step);
	} catch (e) {
		/* ignore */
	}
}

function markResourceStep() {
	const step = resourceOnboardingMap[resource.value?.route];
	if (step) markOnboarding(step);
}
const doc = ref(null);
const savedSnapshot = ref("");
const formEpoch = ref(0);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const formTab = ref(0);
const showAssign = ref(false);
const showQuickEdit = ref(false);
const showSpare = ref(false);
const showReport = ref(false);
const showMobileActions = ref(false);
const connectionsRef = ref(null);
const assignForm = reactive({ engineer: "", visit_date: "" });
const spareForm = reactive({ item_code: "", qty: 1, warehouse: "" });
const reportForm = reactive({ work_done: "" });
const workflow = reactive({
	has_workflow: false,
	transitions: [],
	workflow_state: null,
	docstatus: 0,
	is_submittable: false,
});

const docname = computed(() => route.params.docname || route.params.name || "");
const isNew = computed(() => docname.value === "new");
const isSubmitted = computed(() => Number(doc.value?.docstatus || workflow.docstatus || 0) === 1);
const isCancelled = computed(() => Number(doc.value?.docstatus || 0) === 2);
const amendmentName = computed(() => doc.value?._amendment || "");
const cancelledAlertDescription = computed(() => {
	if (amendmentName.value) {
		return `An amendment already exists (${amendmentName.value}). Open that draft — linked documents should use the amendment, not this cancelled ID.`;
	}
	return "Use Amend to create a new draft. Linked Visit/RMA/Spare docs may still point here until retargeted.";
});
const isDraft = computed(() => !isNew.value && Number(doc.value?.docstatus || 0) === 0);
const isSubmittable = computed(
	() =>
		!!(
			docMeta.value?.is_submittable ||
			workflow.is_submittable ||
			resource.value?.submittable
		),
);
/** Dirty = local edits since last load/save (Desk `__unsaved`). */
const isDirty = computed(() => {
	formEpoch.value; // depend on deep watch ticks
	if (!doc.value) return false;
	if (isNew.value) return true;
	return snapshotDoc(doc.value) !== savedSnapshot.value;
});
/**
 * Desk toolbar.can_submit:
 * draft, not new, submittable, no workflow driving submit.
 */
const canSubmit = computed(
	() =>
		isDraft.value &&
		isSubmittable.value &&
		!workflow.has_workflow &&
		!isDirty.value,
);
const canSave = computed(() => isNew.value || isDraft.value);
const canUpdate = computed(() => isSubmitted.value && isDirty.value);
const canCancel = computed(() => isSubmitted.value);
const canAmend = computed(() => isCancelled.value && isSubmittable.value);
/**
 * Desk get_action_status / set_page_actions:
 * Submit > Save > Update > Cancel(secondary) > Amend
 */
const primaryAction = computed(() => {
	if (isNew.value) {
		return { label: "Save", run: () => save() };
	}
	if (canSubmit.value) {
		return { label: "Submit", run: () => doSubmit() };
	}
	if (canSave.value && (isDirty.value || !isSubmittable.value || workflow.has_workflow)) {
		return { label: "Save", run: () => save() };
	}
	if (canUpdate.value) {
		return { label: "Update", run: () => save() };
	}
	if (canAmend.value) {
		if (amendmentName.value) {
			return {
				label: "Amend",
				disabled: true,
				title: `Already amended as ${amendmentName.value}`,
				run: () => {},
			};
		}
		return { label: "Amend", run: () => doAmend() };
	}
	return null;
});
const secondaryAction = computed(() => {
	if (isNew.value) {
		return { label: "Discard", run: () => goList() };
	}
	// Desk: Cancel is secondary on submitted docs
	if (canCancel.value) {
		return { label: "Cancel", theme: "red", run: () => doCancel() };
	}
	return null;
});

/** Desk `frm.print_doc()` — opens ERPNext print page for this DocType. */
function doPrint() {
	if (!resource.value?.doctype || !doc.value?.name) return;
	openPrintView(resource.value.doctype, doc.value.name);
}

const docstatusLabel = computed(() => {
	const n = Number(doc.value?.docstatus || 0);
	if (n === 1) return "Submitted";
	if (n === 2) return "Cancelled";
	return "Draft";
});
const docstatusTheme = computed(() => {
	const n = Number(doc.value?.docstatus || 0);
	if (n === 1) return "green";
	if (n === 2) return "red";
	return "orange";
});

function snapshotDoc(d) {
	if (!d) return "";
	const skip = new Set([
		"modified",
		"modified_by",
		"_liked_by",
		"_comment_count",
		"_assign",
		"_user_tags",
		"_amendment",
		"_is_cancelled",
		"_remapped_links",
		"_link_impact",
	]);
	const out = {};
	for (const [k, v] of Object.entries(d)) {
		if (skip.has(k) || k.startsWith("__")) continue;
		out[k] = v;
	}
	return JSON.stringify(out);
}

function markClean(d = doc.value) {
	savedSnapshot.value = snapshotDoc(d);
}

const statusValue = computed(() => {
	if (!doc.value) return "";
	if (workflow.workflow_state) return workflow.workflow_state;
	if (resource.value?.statusField) return doc.value[resource.value.statusField];
	return "";
});

const showDocstatusBadge = computed(
	() =>
		!isNew.value &&
		(docMeta.value?.is_submittable || workflow.is_submittable || resource.value?.submittable),
);
const showOpsStatus = computed(() => {
	if (isNew.value || !statusValue.value) return false;
	const ops = statusValue.value;
	return !["Draft", "Submitted", "Cancelled"].includes(ops) && ops !== docstatusLabel.value;
});
const VISIT_STATUS_TRANSITIONS = {
	Draft: ["Scheduled", "Cancelled"],
	Scheduled: ["Travel Started", "Draft", "Cancelled"],
	"Travel Started": ["Reached Site", "Scheduled", "Cancelled"],
	"Reached Site": ["GPS Check-In", "Travel Started", "Cancelled"],
	"GPS Check-In": ["Inspection", "Diagnosis", "Cancelled"],
	Inspection: ["Diagnosis", "GPS Check-In", "Cancelled"],
	Diagnosis: ["Repair", "Testing", "Completed", "Cancelled"],
	Repair: ["Testing", "Diagnosis", "Cancelled"],
	Testing: ["Customer Verification", "Repair", "Cancelled"],
	"Customer Verification": ["GPS Check-Out", "Testing", "Cancelled"],
	"GPS Check-Out": ["Completed", "Customer Verification", "Cancelled"],
	Completed: [],
	Cancelled: [],
	Planned: ["Travel Started", "Scheduled", "Cancelled"],
	Confirmed: ["Travel Started", "Scheduled", "Cancelled"],
	Travel: ["Reached Site", "GPS Check-In", "Cancelled"],
	"In Progress": ["Inspection", "Diagnosis", "GPS Check-Out", "Completed", "Cancelled"],
};
const canEditVisitStatus = computed(
	() => resource.value?.process === "visit" && !isNew.value && !isCancelled.value,
);
const visitStatusOptions = computed(() => {
	if (!canEditVisitStatus.value) return [];
	const current = doc.value?.status || "";
	const next = VISIT_STATUS_TRANSITIONS[current] || [];
	return [current, ...next.filter((s) => s && s !== current)];
});

const hasActions = computed(() => Boolean(resource.value?.process));

const emailSubject = computed(() => {
	const d = doc.value || {};
	const titleKey = resource.value?.titleField || "name";
	const title = d[titleKey] || d.subject || d.name || "";
	const dtype = resource.value?.singular || resource.value?.doctype || "Document";
	return title ? `${dtype}: ${title}` : dtype;
});

const formTabs = computed(() => {
	const tabs = [
		{ label: "Details", icon: LucideLayoutGrid },
		{ label: "Activity", icon: LucideActivity },
		{ label: "Emails", icon: LucideMail },
		{ label: "Comments", icon: LucideMessageSquare },
		{ label: "Data", icon: LucideList },
		{ label: "Notes", icon: LucideStickyNote },
		{ label: "Attachments", icon: LucidePaperclip },
	];
	if (!isNew.value && doc.value?.name) {
		tabs.splice(1, 0, { label: "Connections", icon: LucideLink2 });
	}
	// Engineer Visit: dedicated GPS tab so Check-in / Check-out is always findable
	if (resource.value?.process === "visit" && !isNew.value && doc.value?.name) {
		const insertAt = tabs.findIndex((t) => t.label === "Details") + 1;
		tabs.splice(insertAt, 0, { label: "GPS", icon: LucideMapPin });
	}
	return tabs;
});

const dataTabRows = computed(() => {
	const d = doc.value || {};
	const fields = resource.value?.formFields || [];
	const rows = [];
	const seen = new Set();
	for (const f of fields) {
		if (!f.fieldname || seen.has(f.fieldname)) continue;
		if (["Text", "Long Text", "Small Text", "Text Editor", "Table"].includes(f.fieldtype)) continue;
		seen.add(f.fieldname);
		const label = f.label || f.fieldname;
		let value = d[f.fieldname];
		if (value == null || value === "") value = "—";
		else if (typeof value === "object") value = JSON.stringify(value);
		rows.push({ label, value: String(value) });
	}
	for (const key of ["name", "owner", "creation", "modified", "docstatus"]) {
		if (d[key] == null) continue;
		rows.push({
			label: key.replace(/\b\w/g, (c) => c.toUpperCase()),
			value: String(d[key]),
		});
	}
	return rows;
});

const lifecycleStages = ["Open", "Assigned", "Visit", "Repair", "Closed"];
const lifecycleIndex = computed(() => {
	const s = normalizeSrStatus(statusValue.value || doc.value?.status || "Open");
	if (["Closed", "Cancelled"].includes(s)) return 4;
	if (["Completed", "Customer Verification", "Customer Approval", "Testing"].includes(s)) return 3;
	if (
		[
			"Waiting Spare",
			"Repair In Progress",
			"Repair",
			"Inspection",
			"Waiting Customer",
			"Reached Customer",
			"Reached Site",
		].includes(s)
	)
		return 2;
	if (["Assigned", "Accepted", "Travel Started"].includes(s)) return 1;
	return 0;
});
const lifecycleProgress = computed(
	() => Math.round(((lifecycleIndex.value + 1) / lifecycleStages.length) * 100),
);
const lifecycleHint = computed(() => lifecycleStages[lifecycleIndex.value] || "Open");

function normalizeSrStatus(status) {
	const aliases = {
		"Reached Site": "Reached Customer",
		Repair: "Repair In Progress",
		"Customer Approval": "Customer Verification",
		"Spare Required": "Waiting Spare",
		"Factory Repair": "Repair In Progress",
		"Replacement Required": "Customer Verification",
	};
	return aliases[status] || status || "Open";
}

const srStatus = computed(() => normalizeSrStatus(doc.value?.status || statusValue.value || ""));
const canAssignEngineer = computed(() =>
	["Draft", "Open", "Under Validation"].includes(srStatus.value),
);
const canAdvanceVisit = computed(() =>
	["Assigned", "Accepted", "Travel Started", "Reached Customer", "Reached Site"].includes(
		srStatus.value,
	),
);
const canDiagnose = computed(() =>
	[
		"Inspection",
		"Waiting Customer",
		"Waiting Spare",
		"Repair In Progress",
		"Repair",
		"Testing",
	].includes(srStatus.value),
);
const canBranchOutcomes = computed(() => canDiagnose.value);
const canCloseOut = computed(() =>
	["Completed", "Customer Verification", "Customer Approval", "Closed"].includes(srStatus.value),
);

const eaStatus = computed(() => doc.value?.status || "");
const canAcceptAssignment = computed(() =>
	["Assigned", "Pending Assignment"].includes(eaStatus.value) && Number(doc.value?.docstatus || 0) === 1,
);
const canAdvanceAssignment = computed(() =>
	[
		"Engineer Accepted",
		"Travel Started",
		"Reached Customer",
		"Visit Completed",
	].includes(eaStatus.value),
);
const canSuggestEngineers = computed(
	() =>
		["Draft", "Pending Assignment"].includes(eaStatus.value) ||
		(Number(doc.value?.docstatus || 0) === 0 && !doc.value?.primary_engineer),
);
const engineerSuggestions = ref([]);


const formFields = computed(() => {
	const fields = [...(resource.value?.formFields || [])];
	if (!fields.find((f) => f.fieldname === "naming_series") && docMeta.value?.has_naming_series) {
		fields.unshift({
			section: "Identity",
			fieldname: "naming_series",
			label: "Series",
			fieldtype: "Select",
			reqd: 1,
			options: (docMeta.value.naming_series_options || []).map((o) => ({ label: o, value: o })),
			default: docMeta.value.naming_series_options?.[0],
			read_only: !isNew.value,
		});
	}
	const flags = docMeta.value?.field_flags || {};
	return fields.map((f) => {
		const meta = flags[f.fieldname];
		if (!meta) return f;
		return {
			...f,
			read_only: f.read_only ?? !!meta.read_only,
			allow_on_submit: f.allow_on_submit ?? !!meta.allow_on_submit,
		};
	});
});

const docMeta = ref(null);

function statusTheme(label) {
	const v = (label || "").toLowerCase();
	if (["open", "draft", "planned", "pending", "initiated", "waiting spare", "failed"].includes(v))
		return "orange";
	if (["completed", "closed", "resolved", "active", "approved", "issued", "dispatched"].includes(v))
		return "green";
	if (["cancelled", "rejected"].includes(v)) return "red";
	return "gray";
}

function isOpenLike(label) {
	const v = (label || "").toLowerCase();
	return ["open", "failed", "overdue", "breached"].includes(v);
}

function goList() {
	if (resource.value) router.push({ name: resource.value.listName });
	else router.push("/dashboard");
}

function emptyDoc() {
	const r = resource.value;
	const d = { doctype: r.doctype };
	for (const f of r.formFields || []) {
		d[f.fieldname] = f.default ?? (f.fieldtype === "Check" ? 0 : "");
	}
	// Prefill from route query (ERPNext-style connection create)
	for (const [k, v] of Object.entries(route.query || {})) {
		if (v == null || v === "") continue;
		d[k] = Array.isArray(v) ? v[0] : v;
	}
	const draftKey = "ss_draft_" + r.doctype;
	const draft = sessionStorage.getItem(draftKey);
	if (draft) {
		try {
			Object.assign(d, JSON.parse(draft));
		} catch (e) {
			/* ignore */
		}
		sessionStorage.removeItem(draftKey);
	}
	return d;
}

async function loadWorkflow() {
	if (!resource.value || isNew.value || !doc.value?.name) {
		Object.assign(workflow, {
			has_workflow: false,
			transitions: [],
			workflow_state: null,
			docstatus: 0,
			is_submittable: !!resource.value?.submittable,
		});
		return;
	}
	try {
		const res = await call("swiftservice.api.get_workflow_actions", {
			doctype: resource.value.doctype,
			name: doc.value.name,
		});
		Object.assign(workflow, res || {});
	} catch (e) {
		workflow.has_workflow = false;
		workflow.transitions = [];
	}
}

async function load() {
	if (!resource.value) {
		loading.value = false;
		error.value = "Unknown resource";
		return;
	}
	loading.value = true;
	error.value = "";
	formTab.value = 0;
	try {
		try {
			docMeta.value = await call("swiftservice.api.get_doctype_list_meta", {
				doctype: resource.value.doctype,
			});
			if (docMeta.value?.is_submittable) {
				workflow.is_submittable = true;
			}
		} catch (e) {
			docMeta.value = null;
		}
		if (isNew.value) {
			doc.value = emptyDoc();
			if (docMeta.value?.naming_series_options?.length && !doc.value.naming_series) {
				doc.value.naming_series = docMeta.value.naming_series_options[0];
			}
			markClean(doc.value);
		} else {
			doc.value = await call("swiftservice.api.get_doc", {
				doctype: resource.value.doctype,
				name: docname.value,
			});
			markClean(doc.value);
			await loadWorkflow();
		}
	} catch (e) {
		doc.value = null;
		error.value = e?.messages?.[0] || e?.message || String(e);
		toast.error(error.value);
	} finally {
		loading.value = false;
	}
}

async function save() {
	if (!resource.value) return;
	saving.value = true;
	error.value = "";
	try {
		for (const f of resource.value.formFields || []) {
			if (f.reqd && (doc.value[f.fieldname] === "" || doc.value[f.fieldname] == null)) {
				throw new Error(`${f.label} is required`);
			}
		}
		let result;
		if (isNew.value && resource.value.createMethod) {
			result = await call(resource.value.createMethod, { ...doc.value });
			toast.success("Created");
			markResourceStep();
			await router.replace(`/${resource.value.route}/${encodeURIComponent(result.name)}`);
			await load();
		} else {
			const payload = { ...doc.value, doctype: resource.value.doctype };
			if (isNew.value) delete payload.name;
			result = await call("swiftservice.api.save_doc", {
				doctype: resource.value.doctype,
				doc: payload,
			});
			doc.value = result;
			markClean(result);
			if (result?._remapped_links?.length) {
				toast.success(`Saved (retargeted links: ${result._remapped_links.join("; ")})`);
			} else {
				toast.success(isNew.value ? "Created" : isSubmitted.value ? "Updated" : "Saved");
			}
			if (isNew.value) {
				markResourceStep();
				await router.replace(`/${resource.value.route}/${encodeURIComponent(result.name)}`);
			}
		}
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || String(e);
		toast.error(error.value);
	} finally {
		saving.value = false;
	}
}

function onQuickSaved(result) {
	showQuickEdit.value = false;
	if (result) doc.value = result;
	else load();
	toast.success("Saved");
}

async function runAction(fn) {
	saving.value = true;
	error.value = "";
	try {
		await fn();
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || String(e);
		toast.error(error.value);
	} finally {
		saving.value = false;
	}
}

async function runWorkflow(action) {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.apply_workflow_action", {
			doctype: resource.value.doctype,
			name: doc.value.name,
			action,
		});
		toast.success(`Workflow: ${action}`);
		await loadWorkflow();
	});
}

async function doSubmit() {
	confirmDialog({
		title: "Submit document?",
		message: "Saves your changes, then submits. Submitted documents become read-only.",
		onConfirm: async ({ hideDialog }) => {
			await runAction(async () => {
				// ERPNext Desk: save then submit
				for (const f of resource.value.formFields || []) {
					if (f.reqd && (doc.value[f.fieldname] === "" || doc.value[f.fieldname] == null)) {
						throw new Error(`${f.label} is required`);
					}
				}
				const payload = { ...doc.value, doctype: resource.value.doctype };
				await call("swiftservice.api.save_doc", {
					doctype: resource.value.doctype,
					doc: payload,
				});
				doc.value = await call("swiftservice.api.submit_doc", {
					doctype: resource.value.doctype,
					name: doc.value.name,
				});
				markClean(doc.value);
				toast.success("Submitted");
				await loadWorkflow();
			});
			if (!error.value) hideDialog();
		},
	});
}

async function doCancel() {
	let impactMsg = "This will cancel the submitted document. Linked documents are NOT cancelled automatically.";
	try {
		const impact = await call("swiftservice.api.get_cancel_impact", {
			doctype: resource.value.doctype,
			name: doc.value.name,
		});
		if (impact?.total) {
			const parts = (impact.details || [])
				.map((d) => `${d.doctype}: ${d.count}`)
				.join(", ");
			impactMsg = `This document has ${impact.total} linked record(s) (${parts}). Cancelling will leave those links pointing at a cancelled document and can break detail pages until they are retargeted or amended.`;
		}
	} catch (e) {
		/* ignore impact lookup errors */
	}
	confirmDialog({
		title: "Cancel document?",
		message: impactMsg,
		onConfirm: async ({ hideDialog }) => {
			await runAction(async () => {
				doc.value = await call("swiftservice.api.cancel_doc", {
					doctype: resource.value.doctype,
					name: doc.value.name,
					force: 1,
				});
				markClean(doc.value);
				toast.success("Cancelled");
				await loadWorkflow();
			});
			if (!error.value) hideDialog();
		},
	});
}

async function doAmend() {
	confirmDialog({
		title: "Amend document?",
		message: "Creates a new draft based on this cancelled document.",
		onConfirm: async ({ hideDialog }) => {
			await runAction(async () => {
				const amended = await call("swiftservice.api.amend_doc", {
					doctype: resource.value.doctype,
					name: doc.value.name,
				});
				toast.success(`Amended → ${amended.name}`);
				hideDialog();
				if (resource.value) {
					router.push(`/${resource.value.route}/${encodeURIComponent(amended.name)}`);
				}
			});
		},
	});
}

async function setServiceStatus(status) {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_service_status", {
			service_request: doc.value.name,
			status,
		});
		toast.success(`Status → ${doc.value.status}`);
		await loadWorkflow();
	});
}

async function advanceStatus() {
	await setServiceStatus(undefined);
}

async function acceptAssignment() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.accept_assignment", {
			assignment: doc.value.name,
		});
		toast.success("Assignment accepted");
		await load();
	});
}

async function rejectAssignment() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.reject_assignment", {
			assignment: doc.value.name,
			reason: "Rejected from SPA",
		});
		toast.success("Returned to coordinator queue");
		await load();
	});
}

async function advanceAssignment() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_assignment_status", {
			assignment: doc.value.name,
		});
		toast.success(`Assignment → ${doc.value.status}`);
		await load();
	});
}

async function loadEngineerSuggestions() {
	await runAction(async () => {
		if (!doc.value.service_request) throw new Error("Service Request is required");
		engineerSuggestions.value = await call("swiftservice.api.suggest_engineers", {
			service_request: doc.value.service_request,
			limit: 5,
		});
		if (!engineerSuggestions.value?.length) toast.success("No Active Engineer Profiles found");
	});
}

function applySuggestedEngineer(s) {
	if (!doc.value) return;
	doc.value.primary_engineer = s.engineer;
	doc.value.engineer_profile = s.engineer_profile;
	doc.value.assignment_mode = "Auto Suggested";
	toast.success(`Selected ${s.full_name || s.engineer}`);
}

async function doAssign() {
	await runAction(async () => {
		if (!assignForm.engineer) throw new Error("Engineer is required");
		const res = await call("swiftservice.api.assign_engineer", {
			service_request: doc.value.name,
			engineer: assignForm.engineer,
			visit_date: assignForm.visit_date || undefined,
		});
		showAssign.value = false;
		toast.success(
			res.assignment
				? `Assigned. Assignment ${res.assignment}`
				: `Assigned. Visit ${res.visit} created`,
		);
		markOnboarding("assign_engineer");
		await load();
		if (res.assignment) {
			router.push(`/engineer-assignments/${encodeURIComponent(res.assignment)}`);
		} else if (res.visit) {
			router.push(`/engineer-visits/${encodeURIComponent(res.visit)}`);
		}
	});
}

async function applyDiagnosis() {
	await runAction(async () => {
		if (!doc.value.diagnosis_result) throw new Error("Set Diagnosis Result on the form first");
		doc.value = await call("swiftservice.api.save_doc", {
			doctype: "Swift Service Request",
			doc: doc.value,
		});
		const res = await call("swiftservice.api.update_diagnosis", {
			service_request: doc.value.name,
			diagnosis_result: doc.value.diagnosis_result,
			resolution_summary: doc.value.resolution_summary,
		});
		toast.success(`Diagnosis → ${res.status}`);
		markOnboarding("apply_diagnosis");
		await load();
		if (res.linked?.rma) {
			markOnboarding("start_resolution");
			router.push(`/rma/${encodeURIComponent(res.linked.rma)}`);
		}
		if (res.linked?.replacement) {
			markOnboarding("start_resolution");
			router.push(`/replacements/${encodeURIComponent(res.linked.replacement)}`);
		}
	});
}

async function createSpare() {
	spareForm.item_code = "";
	spareForm.qty = 1;
	spareForm.warehouse = "";
	showSpare.value = true;
}

async function doCreateSpare() {
	await runAction(async () => {
		if (!spareForm.item_code) throw new Error("Item is required");
		const payload = {
			service_request:
				resource.value.doctype === "Swift Service Request"
					? doc.value.name
					: doc.value.service_request,
			item_code: spareForm.item_code,
			qty: spareForm.qty || 1,
			warehouse: spareForm.warehouse || undefined,
		};
		if (resource.value.doctype === "Engineer Visit") {
			payload.engineer_visit = doc.value.name;
			payload.service_request = doc.value.service_request;
		}
		if (resource.value.doctype === "Failure Analysis") {
			payload.diagnosis = doc.value.name;
			payload.engineer_visit = doc.value.engineer_visit || undefined;
		}
		const res = await call("swiftservice.api.create_spare_request", payload);
		showSpare.value = false;
		connectionsRef.value?.reload?.();
		markOnboarding("start_resolution");
		router.push(`/spare-requests/${encodeURIComponent(res.name)}`);
	});
}

async function createRma() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_rma_case", {
			service_request: doc.value.name,
		});
		connectionsRef.value?.reload?.();
		markOnboarding("start_resolution");
		router.push(`/rma/${encodeURIComponent(res.name)}`);
	});
}

async function createReplacement() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_replacement_case", {
			service_request: doc.value.name,
		});
		connectionsRef.value?.reload?.();
		markOnboarding("start_resolution");
		router.push(`/replacements/${encodeURIComponent(res.name)}`);
	});
}

async function createEstimate() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_billing", {
			service_request: doc.value.name,
		});
		connectionsRef.value?.reload?.();
		toast.success(`Billing ${res.name}`);
		router.push(`/billing/${encodeURIComponent(res.name)}`);
	});
}

async function generateBillingFromReport() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_billing", {
			service_request: doc.value.service_request,
			service_report: doc.value.name,
			repair_order: doc.value.repair_order || undefined,
		});
		toast.success(`Billing ${res.name}`);
		router.push(`/billing/${encodeURIComponent(res.name)}`);
	});
}

async function advanceBilling() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_service_billing", { name: doc.value.name });
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function billingApprove() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.billing_approve", {
			name: doc.value.name,
			method: "Portal",
		});
		toast.success("Billing approved");
	});
}

async function billingGenerateInvoice() {
	await runAction(async () => {
		const res = await call("swiftservice.api.billing_generate_invoice", { name: doc.value.name });
		doc.value = res;
		toast.success(
			res.sales_invoice ? `Invoice ${res.sales_invoice}` : `Status → ${res.status}`,
		);
	});
}

async function billingRecordPayment() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.billing_record_payment", {
			name: doc.value.name,
			mode: "UPI",
		});
		toast.success(`Paid · outstanding ${doc.value.outstanding_amount}`);
	});
}

async function billingWarrantySettle() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.billing_warranty_settle", { name: doc.value.name });
		toast.success("Warranty settlement");
	});
}

async function billingCreditNote() {
	await runAction(async () => {
		const res = await call("swiftservice.api.billing_create_credit_note", { name: doc.value.name });
		doc.value = res;
		toast.success(res.credit_note ? `Credit Note ${res.credit_note}` : "Credit note requested");
	});
}

async function createReport() {
	await generateReportFromSSR();
}

async function generateReportFromSSR() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_report", {
			service_request: doc.value.name,
		});
		connectionsRef.value?.reload?.();
		toast.success(`Service Report ${res.name}`);
		router.push(`/service-reports/${encodeURIComponent(res.name)}`);
	});
}

async function generateReportFromVisit() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_report", {
			service_request: doc.value.service_request,
			engineer_visit: doc.value.name,
		});
		toast.success(`Service Report ${res.name}`);
		router.push(`/service-reports/${encodeURIComponent(res.name)}`);
	});
}

async function generateReportFromRepair() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_report", {
			service_request: doc.value.service_request,
			engineer_visit: doc.value.engineer_visit || undefined,
			repair_order: doc.value.name,
		});
		toast.success(`Service Report ${res.name}`);
		router.push(`/service-reports/${encodeURIComponent(res.name)}`);
	});
}

async function doCreateReport() {
	await generateReportFromSSR();
	showReport.value = false;
}

async function advanceServiceReport() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_service_report", { name: doc.value.name });
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function srptEngineerReview() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.service_report_engineer_review", { name: doc.value.name });
		toast.success("Engineer review done");
	});
}

async function srptCustomerSign() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.service_report_customer_sign", {
			name: doc.value.name,
			refused: doc.value.signature_refused ? 1 : 0,
			refusal_reason: doc.value.refusal_reason || undefined,
			contact_name: doc.value.customer_contact_name || undefined,
			signature: doc.value.customer_signature || undefined,
		});
		toast.success("Customer sign-off recorded");
	});
}

async function srptManagerVerify() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.service_report_manager_verify", { name: doc.value.name });
		toast.success("Manager verified");
	});
}

async function srptBillingReady() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.service_report_billing_ready", { name: doc.value.name });
		toast.success("Billing ready");
	});
}

async function srptCreateRevision() {
	await runAction(async () => {
		const res = await call("swiftservice.api.service_report_create_revision", { name: doc.value.name });
		toast.success(`Revision ${res.revision} → ${res.name}`);
		router.push(`/service-reports/${encodeURIComponent(res.name)}`);
	});
}

async function createFeedback() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_feedback", {
			service_request: doc.value.name,
			customer: doc.value.customer,
		});
		connectionsRef.value?.reload?.();
		toast.success(`Feedback ${res.name}`);
		router.push(`/feedback/${encodeURIComponent(res.name)}`);
	});
}

async function generateFeedbackFromReport() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_feedback", {
			service_request: doc.value.service_request,
			service_report: doc.value.name,
		});
		toast.success(`Feedback ${res.name}`);
		router.push(`/feedback/${encodeURIComponent(res.name)}`);
	});
}

async function generateFeedbackFromBilling() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_feedback", {
			service_request: doc.value.service_request,
			service_report: doc.value.service_report || undefined,
			service_billing: doc.value.name,
		});
		toast.success(`Feedback ${res.name}`);
		router.push(`/feedback/${encodeURIComponent(res.name)}`);
	});
}

async function advanceFeedback() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_feedback", { name: doc.value.name });
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function feedbackRequest() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.feedback_request", { name: doc.value.name });
		toast.success("Feedback requested");
	});
}

async function feedbackSubmitResponse() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.feedback_submit_response", {
			name: doc.value.name,
			csat_rating: doc.value.csat_rating || doc.value.rating || 4,
			nps_score: doc.value.nps_score ?? 8,
			issue_resolved: doc.value.issue_resolved || "Yes",
			positive_feedback: doc.value.positive_feedback || doc.value.feedback_text || undefined,
			complaint_text: doc.value.complaint_text || undefined,
			suggestions: doc.value.suggestions || undefined,
			would_recommend_us: doc.value.would_recommend_us || undefined,
			would_call_again: doc.value.would_call_again || undefined,
			complaint_against_engineer: doc.value.complaint_against_engineer ? 1 : 0,
			complaint_category: doc.value.complaint_category || undefined,
			complaint_details: doc.value.complaint_details || undefined,
		});
		toast.success(
			doc.value.escalation_required
				? `Responded · Escalation ${doc.value.escalation_status}`
				: `Responded · ${doc.value.nps_category || "OK"}`,
		);
	});
}

async function feedbackReview() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.feedback_review", { name: doc.value.name });
		toast.success("Reviewed");
	});
}

async function feedbackResolveEscalation() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.feedback_resolve_escalation", { name: doc.value.name });
		toast.success("Escalation resolved");
	});
}

async function feedbackClose() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.feedback_close", { name: doc.value.name });
		toast.success("Feedback closed");
	});
}

async function feedbackCreateRevision() {
	await runAction(async () => {
		const res = await call("swiftservice.api.feedback_create_revision", { name: doc.value.name });
		toast.success(`Revision ${res.revision} → ${res.name}`);
		router.push(`/feedback/${encodeURIComponent(res.name)}`);
	});
}

async function generateClosureFromSSR() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_closure", {
			service_request: doc.value.name,
		});
		toast.success(`Closure ${res.name}`);
		router.push(`/service-closures/${encodeURIComponent(res.name)}`);
	});
}

async function generateClosureFromFeedback() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_service_closure", {
			service_request: doc.value.service_request,
		});
		toast.success(`Closure ${res.name}`);
		router.push(`/service-closures/${encodeURIComponent(res.name)}`);
	});
}

async function advanceClosure() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_service_closure", { name: doc.value.name });
		toast.success(doc.value.status);
	});
}

async function closureRunValidation() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.closure_run_validation", { name: doc.value.name });
		toast.success(doc.value.validation_passed ? "Validation passed" : "Validation failed");
	});
}

async function closureApprove() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.closure_approve", {
			name: doc.value.name,
			remarks: doc.value.approval_remarks || undefined,
		});
		toast.success("Closure approved");
	});
}

async function closureExecuteClose() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.closure_execute_close", {
			name: doc.value.name,
			closure_reason: doc.value.closure_reason || undefined,
		});
		toast.success("Service Request closed");
	});
}

async function closureArchive() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.closure_archive", { name: doc.value.name });
		toast.success("Archived");
	});
}

async function closureRequestReopen() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.closure_request_reopen", {
			name: doc.value.name,
			reason: doc.value.reopen_reason || "Wrong Closure",
		});
		toast.success("Reopen requested");
	});
}

async function closureApproveReopen() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.closure_approve_reopen", { name: doc.value.name });
		toast.success("Service Request reopened");
	});
}

const visitOutcomes = [
	"Fixed",
	"Spare Required",
	"Workshop Repair",
	"Replacement",
	"Software Issue",
	"Calibration Needed",
	"No Fault Found",
	"Customer Not Available",
];

function onGpsUpdated(updated) {
	if (updated) {
		doc.value = updated;
		markClean(updated);
	} else {
		load();
	}
	markOnboarding("check_in_visit");
}

async function getGeoStrict() {
	return new Promise((resolve, reject) => {
		if (!navigator.geolocation) {
			reject(new Error("GPS not supported on this device"));
			return;
		}
		navigator.geolocation.getCurrentPosition(
			(pos) =>
				resolve({
					gps_lat: pos.coords.latitude,
					gps_lng: pos.coords.longitude,
					gps_accuracy: pos.coords.accuracy,
				}),
			(err) => {
				const msg =
					err?.code === 1
						? "Location permission denied. Enable GPS for this site."
						: "Could not read GPS location";
				reject(new Error(msg));
			},
			{ enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
		);
	});
}

async function mobileCheckIn() {
	await runAction(async () => {
		const geo = await getGeoStrict();
		doc.value = await call("swiftservice.api.check_in_visit", {
			name: doc.value.name,
			...geo,
			force: 1,
		});
		markClean(doc.value);
		toast.success("Checked in");
		markOnboarding("check_in_visit");
	});
}

async function mobileCheckOut() {
	await runAction(async () => {
		const geo = await getGeoStrict();
		doc.value = await call("swiftservice.api.check_out_visit", {
			name: doc.value.name,
			diagnosis_notes: doc.value.diagnosis_notes || doc.value.work_done,
			gps_lat: geo.gps_lat,
			gps_lng: geo.gps_lng,
		});
		markClean(doc.value);
		toast.success("Checked out");
	});
}

async function advanceVisit() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_visit_status", {
			name: doc.value.name,
		});
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function onVisitStatusChange(e) {
	const status = e?.target?.value;
	if (!status || status === doc.value?.status) return;
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_visit_status", {
			name: doc.value.name,
			status,
		});
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function createFollowUpVisit() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_followup_visit", {
			source_visit: doc.value.name,
		});
		toast.success(`Follow-up Visit ${res.name} created`);
		router.push(`/engineer-visits/${encodeURIComponent(res.name)}`);
	});
}

async function setVisitOutcome(result) {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.save_doc", {
			doctype: resource.value.doctype,
			doc: { ...doc.value, diagnosis_result: result },
		});
		toast.success(`Outcome: ${result}`);
	});
}

async function openDiagnosisFromVisit() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_diagnosis", {
			engineer_visit: doc.value.name,
			force: 1,
		});
		toast.success(`Diagnosis ${res.name}`);
		router.push(`/diagnoses/${encodeURIComponent(res.name)}`);
	});
}

async function createSpareFromVisit() {
	showSpare.value = true;
	spareForm.item_code = doc.value.item_code || "";
	spareForm.qty = 1;
	spareForm.warehouse = "";
}

async function advanceDiagnosis() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_diagnosis_status", {
			name: doc.value.name,
		});
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function createSpareFromDiagnosis() {
	await runAction(async () => {
		if (!doc.value.service_request) throw new Error("Service Request is required");
		const res = await call("swiftservice.api.create_spare_request", {
			service_request: doc.value.service_request,
			engineer_visit: doc.value.engineer_visit || undefined,
			diagnosis: doc.value.name,
			item_code: doc.value.item_code || undefined,
			qty: 1,
		});
		toast.success(`Spare Request ${res.name}`);
		router.push(`/spare-requests/${encodeURIComponent(res.name)}`);
	});
}

async function createRepairFromDiagnosis() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_repair_order", {
			service_request: doc.value.service_request,
			engineer_visit: doc.value.engineer_visit || undefined,
			diagnosis: doc.value.name,
			repair_type: "Warranty",
		});
		toast.success(`Repair Order ${res.name}`);
		router.push(`/repair-orders/${encodeURIComponent(res.name)}`);
	});
}

async function createRepairFromVisit() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_repair_order", {
			service_request: doc.value.service_request,
			engineer_visit: doc.value.name,
			repair_type: "Warranty",
		});
		toast.success(`Repair Order ${res.name}`);
		router.push(`/repair-orders/${encodeURIComponent(res.name)}`);
	});
}

async function advanceRepair() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_repair_status", { name: doc.value.name });
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function repairReceived() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_mark_received", { name: doc.value.name });
		toast.success("Received at workshop");
	});
}

async function repairStart() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_start", { name: doc.value.name });
		toast.success("Repair started");
	});
}

async function repairComplete() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_complete", { name: doc.value.name });
		toast.success("Repair completed");
	});
}

async function repairPassTesting() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_pass_testing", { name: doc.value.name });
		toast.success("Testing passed");
	});
}

async function repairPassQuality() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_pass_quality", {
			name: doc.value.name,
			result: "Pass",
		});
		toast.success("Quality passed");
	});
}

async function repairDispatch() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_dispatch", { name: doc.value.name });
		toast.success(
			doc.value.installation_visit
				? `Dispatched · Visit ${doc.value.installation_visit}`
				: "Dispatched",
		);
	});
}

async function repairRecommendReplacement() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.repair_recommend_replacement", {
			name: doc.value.name,
			ber: doc.value.ber_flag ? 1 : 0,
		});
		toast.success("Replacement recommended");
	});
}

async function advanceSpare() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_spare_status", {
			name: doc.value.name,
		});
		toast.success(`Status → ${doc.value.status}`);
	});
}

async function receiveSpare() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.receive_spare", { name: doc.value.name });
		toast.success("Marked received by engineer");
	});
}

async function consumeSpare() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.consume_spare", { name: doc.value.name });
		toast.success("Marked consumed");
	});
}

async function createSpareMR() {
	await runAction(async () => {
		const res = await call("swiftservice.api.create_spare_purchase_request", {
			name: doc.value.name,
		});
		doc.value = res;
		toast.success(res.purchase_request ? `MR ${res.purchase_request}` : "Purchase request updated");
	});
}

async function approveSpare() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.approve_spare_request", { name: doc.value.name });
		toast.success("Approved");
	});
}

async function issueSpare() {
	await runAction(async () => {
		const res = await call("swiftservice.api.issue_spare", { name: doc.value.name });
		toast.success(res.material_request ? `Issued. MR ${res.material_request}` : "Spare issued");
		await load();
	});
}

async function advanceRma(status) {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.advance_rma", {
			name: doc.value.name,
			repair_status: status,
		});
		toast.success(`RMA → ${status}`);
	});
}

async function approveRep(level) {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.approve_replacement", {
			name: doc.value.name,
			level,
		});
		toast.success(doc.value.approval_status);
	});
}

async function completeRep() {
	await runAction(async () => {
		doc.value = await call("swiftservice.api.complete_replacement", {
			name: doc.value.name,
			new_serial_no: doc.value.new_serial_no,
			old_serial_no: doc.value.old_serial_no,
		});
		toast.success("Replacement completed");
	});
}

async function createInvoice() {
	await runAction(async () => {
		const payload =
			resource.value?.process === "billing"
				? {
						service_request: doc.value.service_request,
						billing_name: doc.value.name,
					}
				: {
						service_request: doc.value.service_request,
						estimate_name: doc.value.name,
					};
		const res = await call("swiftservice.api.create_service_invoice", payload);
		toast.success(`Invoice ${res.sales_invoice} (₹${res.grand_total})`);
		await load();
	});
}

watch(
	() => [docname.value, resourceKey.value],
	() => load(),
);
watch(
	doc,
	() => {
		formEpoch.value += 1;
	},
	{ deep: true },
);
onMounted(load);
</script>
