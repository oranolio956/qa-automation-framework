import { render, screen } from '@testing-library/react';
import HomePage from '../app/page';

test('renders heading', () => {
  render(<HomePage />);
  expect(screen.getByText('Contractor Registration')).toBeInTheDocument();
});