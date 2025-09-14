import { createSchema, createYoga } from 'graphql-yoga';

const typeDefs = /* GraphQL */ `
  type Query {
    ping: String!
  }
`;

const resolvers = {
  Query: {
    ping: () => 'pong'
  }
};

const { handleRequest } = createYoga({
  schema: createSchema({ typeDefs, resolvers }),
  graphqlEndpoint: '/api/graphql'
});

export { handleRequest as GET, handleRequest as POST };

