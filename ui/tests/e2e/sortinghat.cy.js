describe('SortingHat', () => {
  it('Loads the "identities" section', () => {
    cy.setCookie('csrftoken', 'testToken')
    cy.setCookie('gl_user', 'testUser')
    cy.visit('/identities')

    cy.get('main')
      .should('contain', 'Workspace')
      .should('contain', 'Individuals')
      .should('contain', 'Organizations')
  })
})
