/**
 * Janitor Monitor Hook for MyCasa Pro
 * Runs periodic audits and monitors agent health
 */

const { execSync } = require('child_process');
const path = require('path');

const WORKDIR = '/Users/chefmbororo/clawd/apps/mycasa-pro';

/**
 * Execute a MyCasa CLI command and return JSON result
 */
function execMyCasa(agent, command, args = {}) {
    try {
        const argsJson = JSON.stringify(args);
        const cmd = `cd ${WORKDIR} && source venv/bin/activate && python3 mycasa_cli.py ${agent} ${command} --args '${argsJson}'`;
        const result = execSync(cmd, { encoding: 'utf-8', timeout: 30000 });
        return JSON.parse(result);
    } catch (error) {
        return { error: error.message };
    }
}

/**
 * Run Janitor audit
 */
function runAudit() {
    return execMyCasa('janitor', 'run_audit');
}

/**
 * Get Janitor status
 */
function getStatus() {
    return execMyCasa('janitor', 'get_status');
}

/**
 * Check all agents health
 */
function checkAllAgentsHealth() {
    const agents = ['manager', 'janitor', 'finance', 'maintenance', 'contractors', 'projects'];
    const health = {};
    
    for (const agent of agents) {
        try {
            const status = execMyCasa(agent, 'get_status');
            health[agent] = {
                status: status.error ? 'error' : 'healthy',
                data: status
            };
        } catch (e) {
            health[agent] = { status: 'error', error: e.message };
        }
    }
    
    return health;
}

/**
 * Hook: Pre-task check
 * Validates system health before task execution
 */
function preTaskHook(taskInfo) {
    const janitorStatus = getStatus();
    
    if (janitorStatus.metrics && janitorStatus.metrics.issues > 0) {
        console.warn(`[Janitor] ${janitorStatus.metrics.issues} active issues detected`);
    }
    
    return {
        canProceed: true,
        warnings: janitorStatus.metrics?.issues || 0,
        janitorStatus
    };
}

/**
 * Hook: Post-task check
 * Records task outcome and checks for new issues
 */
function postTaskHook(taskInfo, outcome) {
    // Run quick correctness check after task
    const correctness = execMyCasa('janitor', 'check_correctness');
    
    return {
        correctnessIssues: correctness.length || 0,
        issues: correctness
    };
}

/**
 * Hook: Periodic audit (called by daemon)
 */
function periodicAudit() {
    console.log('[Janitor] Running periodic audit...');
    const audit = runAudit();
    
    if (audit.summary) {
        const { p0_count, p1_count, total_findings } = audit.summary;
        
        if (p0_count > 0 || p1_count > 0) {
            console.error(`[Janitor] ALERT: ${p0_count} P0 and ${p1_count} P1 issues found!`);
        }
        
        console.log(`[Janitor] Audit complete: ${total_findings} findings`);
    }
    
    return audit;
}

module.exports = {
    runAudit,
    getStatus,
    checkAllAgentsHealth,
    preTaskHook,
    postTaskHook,
    periodicAudit,
    execMyCasa
};
