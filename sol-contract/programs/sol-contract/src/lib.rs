pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;


pub use constants::*;
pub use instructions::*;
pub use state::*;

declare_id!("FYLQ37BMWhdhqDpieatcdrujk9ZVW6GfujxeAhCy4WZv");

#[program]
pub mod sol_contract {
    use super::*;
    pub fn initialize(ctx: Context<Initialize>, owner_name: String) -> Result<()> {
        initialize::handler(ctx, owner_name)
    }
}
