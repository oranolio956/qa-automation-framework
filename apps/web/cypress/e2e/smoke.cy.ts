describe('homepage', () => {
  it('shows heading', () => {
    cy.visit('/');
    cy.contains('Contractor Registration').should('be.visible');
  });
});